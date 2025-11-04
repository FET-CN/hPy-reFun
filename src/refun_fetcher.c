// refun_fetcher.c - reFun 包管理器的文件下载和对象存储实现
// 提供从多个源获取文件和对象池管理功能

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/stream.h"
#include "refun_fetcher.h"
#include "refun_utils.h"

#include <string.h>

// ============================================================================
// 内部辅助函数：计算文件的 SHA256 哈希值
// ============================================================================

static mp_obj_t compute_file_hash(mp_obj_t file_path_obj) {
    // 导入 uhashlib 模块
    mp_obj_t uhashlib_module = mp_import_name(MP_QSTR_uhashlib, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t sha256_class = mp_load_attr(uhashlib_module, MP_QSTR_sha256);

    // 创建 sha256 对象
    mp_obj_t hasher = mp_call_function_0(sha256_class);

    // 打开文件
    mp_obj_t args[2] = {file_path_obj, MP_OBJ_NEW_QSTR(MP_QSTR_rb)};
    mp_obj_t file_obj = mp_builtin_open(2, args, (mp_map_t *)&mp_const_empty_map);

    // 读取文件并更新哈希
    mp_obj_t update_method = mp_load_attr(hasher, MP_QSTR_update);

    // 分块读取（避免大文件占用内存）
    const size_t CHUNK_SIZE = 4096;
    uint8_t buffer[CHUNK_SIZE];
    int errcode;

    while (true) {
        mp_uint_t bytes_read = mp_stream_read(file_obj, buffer, CHUNK_SIZE, &errcode);
        if (bytes_read == 0) break;

        mp_obj_t chunk = mp_obj_new_bytes(buffer, bytes_read);
        mp_call_function_1(update_method, chunk);
    }

    // 关闭文件
    mp_stream_close(file_obj);

    // 获取十六进制摘要
    mp_obj_t hexdigest_method = mp_load_attr(hasher, MP_QSTR_hexdigest);
    return mp_call_function_0(hexdigest_method);
}

// ============================================================================
// 内部辅助函数：根据哈希值生成对象路径
// ============================================================================

static mp_obj_t get_hash_object_path(mp_obj_t storage_path, mp_obj_t hash_obj) {
    const char *hash_str = mp_obj_str_get_str(hash_obj);

    // 检查哈希长度
    if (strlen(hash_str) < 3) {
        mp_raise_ValueError(MP_ERROR_TEXT("Hash too short"));
    }

    // 创建路径：storage_path / hash[:2] / hash[2:]
    char dir_part[3] = {hash_str[0], hash_str[1], '\0'};
    const char *file_part = hash_str + 2;

    mp_obj_t dir_obj = mp_obj_new_str(dir_part, 2);
    mp_obj_t file_obj = mp_obj_new_str(file_part, strlen(file_part));

    // 使用 refun.path_join
    mp_obj_t path_args[3] = {storage_path, dir_obj, file_obj};
    return refun_path_join(3, path_args);
}

// ============================================================================
// 内部辅助函数：创建目录（递归）
// ============================================================================

static void ensure_directory(mp_obj_t dir_path) {
    nlr_buf_t nlr;

    if (nlr_push(&nlr) == 0) {
        // 尝试创建目录
        mp_obj_t os_module = mp_import_name(MP_QSTR_os, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t makedirs_func = mp_load_attr(os_module, MP_QSTR_makedirs);
        mp_call_function_1(makedirs_func, dir_path);
        nlr_pop();
    } else {
        // 如果已存在，忽略错误
        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
        if (!mp_obj_is_type(exc, &mp_type_OSError)) {
            nlr_raise(exc);
        }
    }
}

// ============================================================================
// 内部辅助函数：获取目录路径
// ============================================================================

static mp_obj_t get_dirname(mp_obj_t path_obj) {
    const char *path = mp_obj_str_get_str(path_obj);
    const char *last_sep = strrchr(path, '/');

    if (last_sep == NULL) {
        last_sep = strrchr(path, '\\');
    }

    if (last_sep == NULL) {
        return mp_obj_new_str(".", 1);
    }

    size_t dir_len = last_sep - path;
    return mp_obj_new_str(path, dir_len);
}

// ============================================================================
// Fetcher 构造函数
// ============================================================================

static mp_obj_t refun_fetcher_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 2, false);

    // 创建 Fetcher 对象
    refun_fetcher_obj_t *self = mp_obj_malloc(refun_fetcher_obj_t, type);

    // 保存路径
    self->storage_path = args[0];
    self->cache_path = (n_args > 1) ? args[1] : mp_const_none;

    // 确保存储目录存在
    ensure_directory(self->storage_path);

    return MP_OBJ_FROM_PTR(self);
}

// ============================================================================
// Fetcher.get_object_path(hash_value) - 获取对象路径
// ============================================================================

static mp_obj_t refun_fetcher_get_object_path(mp_obj_t self_in, mp_obj_t hash_obj) {
    refun_fetcher_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return get_hash_object_path(self->storage_path, hash_obj);
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_fetcher_get_object_path_obj, refun_fetcher_get_object_path);

// ============================================================================
// Fetcher.has_object(hash_value) - 检查对象是否存在
// ============================================================================

static mp_obj_t refun_fetcher_has_object(mp_obj_t self_in, mp_obj_t hash_obj) {
    mp_obj_t obj_path = refun_fetcher_get_object_path(self_in, hash_obj);

    nlr_buf_t nlr;
    bool exists = false;

    if (nlr_push(&nlr) == 0) {
        // 尝试获取文件状态
        mp_obj_t os_module = mp_import_name(MP_QSTR_os, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t stat_func = mp_load_attr(os_module, MP_QSTR_stat);
        mp_call_function_1(stat_func, obj_path);
        exists = true;
        nlr_pop();
    } else {
        // 文件不存在
        mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(nlr.ret_val));
    }

    return mp_obj_new_bool(exists);
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_fetcher_has_object_obj, refun_fetcher_has_object);

// ============================================================================
// Fetcher.store_file(src_path, expected_hash) - 存储本地文件
// ============================================================================

static mp_obj_t refun_fetcher_store_file(mp_obj_t self_in, mp_obj_t src_path_obj, mp_obj_t expected_hash_obj) {
    refun_fetcher_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 计算文件哈希
    mp_obj_t actual_hash = compute_file_hash(src_path_obj);

    // 验证哈希
    if (!mp_obj_equal(actual_hash, expected_hash_obj)) {
        mp_raise_msg_varg(&mp_type_ValueError,
            MP_ERROR_TEXT("Hash mismatch: expected %s, got %s"),
            mp_obj_str_get_str(expected_hash_obj),
            mp_obj_str_get_str(actual_hash));
    }

    // 获取目标路径
    mp_obj_t dest_path = get_hash_object_path(self->storage_path, actual_hash);

    // 如果已存在，直接返回
    if (refun_fetcher_has_object(self_in, actual_hash) == mp_const_true) {
        return dest_path;
    }

    // 确保目标目录存在
    mp_obj_t dest_dir = get_dirname(dest_path);
    ensure_directory(dest_dir);

    // 复制文件
    // 打开源文件
    mp_obj_t src_args[2] = {src_path_obj, MP_OBJ_NEW_QSTR(MP_QSTR_rb)};
    mp_obj_t src_file = mp_builtin_open(2, src_args, (mp_map_t *)&mp_const_empty_map);

    // 打开目标文件
    mp_obj_t dest_args[2] = {dest_path, MP_OBJ_NEW_QSTR(MP_QSTR_wb)};
    mp_obj_t dest_file = mp_builtin_open(2, dest_args, (mp_map_t *)&mp_const_empty_map);

    // 分块复制
    const size_t CHUNK_SIZE = 4096;
    uint8_t buffer[CHUNK_SIZE];
    int errcode;

    while (true) {
        mp_uint_t bytes_read = mp_stream_read(src_file, buffer, CHUNK_SIZE, &errcode);
        if (bytes_read == 0) break;

        mp_stream_write_exactly(dest_file, buffer, bytes_read, &errcode);
    }

    // 关闭文件
    mp_stream_close(src_file);
    mp_stream_close(dest_file);

    return dest_path;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_fetcher_store_file_obj, refun_fetcher_store_file);

// ============================================================================
// Fetcher.fetch(sources, expected_hash) - 从多个源获取文件
// ============================================================================

static mp_obj_t refun_fetcher_fetch(size_t n_args, const mp_obj_t *args) {
    refun_fetcher_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t sources_obj = args[1];
    mp_obj_t expected_hash_obj = args[2];

    // 检查是否已有对象
    if (refun_fetcher_has_object(args[0], expected_hash_obj) == mp_const_true) {
        return refun_fetcher_get_object_path(args[0], expected_hash_obj);
    }

    // 将 sources 转为列表
    mp_obj_t iter = mp_getiter(sources_obj, NULL);
    mp_obj_t source;
    mp_obj_t last_error = mp_const_none;

    // 依次尝试每个源
    while ((source = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
        nlr_buf_t nlr;

        if (nlr_push(&nlr) == 0) {
            // 尝试从该源获取
            // 如果是本地路径，直接使用 store_file
            mp_obj_t result = refun_fetcher_store_file(args[0], source, expected_hash_obj);
            nlr_pop();
            return result;
        } else {
            // 该源失败，记录错误并尝试下一个
            last_error = MP_OBJ_FROM_PTR(nlr.ret_val);
        }
    }

    // 所有源都失败
    if (last_error != mp_const_none) {
        nlr_raise(last_error);
    }

    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("No valid source found"));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_fetcher_fetch_obj, 3, 3, refun_fetcher_fetch);

// ============================================================================
// Fetcher 类型的本地字典（方法表）
// ============================================================================

static const mp_rom_map_elem_t refun_fetcher_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_fetch), MP_ROM_PTR(&refun_fetcher_fetch_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_object_path), MP_ROM_PTR(&refun_fetcher_get_object_path_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_object), MP_ROM_PTR(&refun_fetcher_has_object_obj) },
    { MP_ROM_QSTR(MP_QSTR_store_file), MP_ROM_PTR(&refun_fetcher_store_file_obj) },
};
static MP_DEFINE_CONST_DICT(refun_fetcher_locals_dict, refun_fetcher_locals_dict_table);

// ============================================================================
// Fetcher 类型定义
// ============================================================================

MP_DEFINE_CONST_OBJ_TYPE(
    refun_fetcher_type,
    MP_QSTR_Fetcher,
    MP_TYPE_FLAG_NONE,
    make_new, refun_fetcher_make_new,
    locals_dict, &refun_fetcher_locals_dict
);
