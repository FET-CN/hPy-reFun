// refun_registry.c - reFun 包管理器的注册表管理实现
// 提供包的注册、查询和持久化功能

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objdict.h"
#include "py/stream.h"
#include "refun_registry.h"

#include <string.h>

// ============================================================================
// Registry 构造函数
// ============================================================================

static mp_obj_t refun_registry_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 1, false);

    // 创建 Registry 对象
    refun_registry_obj_t *self = mp_obj_malloc(refun_registry_obj_t, type);

    // 保存注册表路径
    self->registry_path = args[0];

    // 初始化数据为空字典
    self->data = mp_obj_new_dict(0);
    self->dirty = false;
    self->loaded = false;

    return MP_OBJ_FROM_PTR(self);
}

// ============================================================================
// Registry.load() - 从文件加载注册表
// ============================================================================

static mp_obj_t refun_registry_load(mp_obj_t self_in) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 如果已加载，直接返回
    if (self->loaded) {
        return mp_const_none;
    }

    // 获取路径字符串
    const char *path = mp_obj_str_get_str(self->registry_path);

    // 尝试打开文件
    mp_obj_t args[2] = {
        self->registry_path,
        MP_OBJ_NEW_QSTR(MP_QSTR_r)
    };

    mp_obj_t file_obj = mp_const_none;
    nlr_buf_t nlr;

    // 尝试打开文件，如果失败则创建空注册表
    if (nlr_push(&nlr) == 0) {
        file_obj = mp_builtin_open(2, args, (mp_map_t *)&mp_const_empty_map);
        nlr_pop();
    } else {
        // 文件不存在，使用空字典
        self->data = mp_obj_new_dict(0);
        self->loaded = true;
        return mp_const_none;
    }

    // 读取文件内容
    int errcode;
    mp_uint_t file_size = mp_stream_posix_lseek((mp_obj_t)file_obj, 0, SEEK_END, &errcode);
    mp_stream_posix_lseek((mp_obj_t)file_obj, 0, SEEK_SET, &errcode);

    vstr_t vstr;
    vstr_init_len(&vstr, file_size);
    mp_stream_read_exactly((mp_obj_t)file_obj, vstr.buf, file_size, &errcode);

    // 关闭文件
    mp_stream_close(file_obj);

    // 解析 JSON
    mp_obj_t json_str = mp_obj_new_str_from_vstr(&mp_type_str, &vstr);

    // 导入 ujson 模块
    mp_obj_t ujson_module = mp_import_name(MP_QSTR_ujson, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t loads_method = mp_load_attr(ujson_module, MP_QSTR_loads);

    // 调用 ujson.loads()
    self->data = mp_call_function_1(loads_method, json_str);
    self->loaded = true;
    self->dirty = false;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_registry_load_obj, refun_registry_load);

// ============================================================================
// Registry.save() - 保存注册表到文件
// ============================================================================

static mp_obj_t refun_registry_save(mp_obj_t self_in) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 如果数据未修改，跳过保存
    if (!self->dirty) {
        return mp_const_none;
    }

    // 导入 ujson 模块
    mp_obj_t ujson_module = mp_import_name(MP_QSTR_ujson, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t dumps_method = mp_load_attr(ujson_module, MP_QSTR_dumps);

    // 调用 ujson.dumps()
    mp_obj_t json_str = mp_call_function_1(dumps_method, self->data);

    // 打开文件写入
    mp_obj_t args[2] = {
        self->registry_path,
        MP_OBJ_NEW_QSTR(MP_QSTR_w)
    };
    mp_obj_t file_obj = mp_builtin_open(2, args, (mp_map_t *)&mp_const_empty_map);

    // 写入数据
    const char *json_data = mp_obj_str_get_str(json_str);
    size_t json_len = mp_obj_str_get_len(json_str);

    int errcode;
    mp_stream_write_exactly((mp_obj_t)file_obj, json_data, json_len, &errcode);

    // 关闭文件
    mp_stream_close(file_obj);

    self->dirty = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_registry_save_obj, refun_registry_save);

// ============================================================================
// Registry.add_package(name, version, metadata) - 注册包
// ============================================================================

static mp_obj_t refun_registry_add_package(size_t n_args, const mp_obj_t *args) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name_obj = args[1];
    mp_obj_t version_obj = args[2];
    mp_obj_t metadata_obj = args[3];

    // 确保已加载
    if (!self->loaded) {
        refun_registry_load(args[0]);
    }

    // 获取或创建包的版本字典
    mp_obj_dict_t *data_dict = MP_OBJ_TO_PTR(self->data);
    mp_map_elem_t *pkg_elem = mp_map_lookup(&data_dict->map, name_obj, MP_MAP_LOOKUP_ADD_IF_MISSING);

    if (pkg_elem->value == MP_OBJ_NULL) {
        // 创建新的版本字典
        pkg_elem->value = mp_obj_new_dict(0);
    }

    // 添加版本和元数据
    mp_obj_dict_t *version_dict = MP_OBJ_TO_PTR(pkg_elem->value);
    mp_map_elem_t *ver_elem = mp_map_lookup(&version_dict->map, version_obj, MP_MAP_LOOKUP_ADD_IF_MISSING);
    ver_elem->value = metadata_obj;

    self->dirty = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_registry_add_package_obj, 4, 4, refun_registry_add_package);

// ============================================================================
// Registry.remove_package(name, version) - 删除包
// ============================================================================

static mp_obj_t refun_registry_remove_package(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 确保已加载
    if (!self->loaded) {
        refun_registry_load(self_in);
    }

    // 查找包
    mp_obj_dict_t *data_dict = MP_OBJ_TO_PTR(self->data);
    mp_map_elem_t *pkg_elem = mp_map_lookup(&data_dict->map, name_obj, MP_MAP_LOOKUP);

    if (pkg_elem == NULL) {
        mp_raise_msg_varg(&mp_type_KeyError, MP_ERROR_TEXT("Package '%s' not found"), mp_obj_str_get_str(name_obj));
    }

    // 删除版本
    mp_obj_dict_t *version_dict = MP_OBJ_TO_PTR(pkg_elem->value);
    mp_map_elem_t *ver_elem = mp_map_lookup(&version_dict->map, version_obj, MP_MAP_LOOKUP_REMOVE_IF_FOUND);

    if (ver_elem == NULL) {
        mp_raise_msg_varg(&mp_type_KeyError, MP_ERROR_TEXT("Version '%s' not found"), mp_obj_str_get_str(version_obj));
    }

    // 如果版本字典为空，删除整个包
    if (version_dict->map.used == 0) {
        mp_map_lookup(&data_dict->map, name_obj, MP_MAP_LOOKUP_REMOVE_IF_FOUND);
    }

    self->dirty = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_registry_remove_package_obj, refun_registry_remove_package);

// ============================================================================
// Registry.get_package(name, version) - 获取包元数据
// ============================================================================

static mp_obj_t refun_registry_get_package(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 确保已加载
    if (!self->loaded) {
        refun_registry_load(self_in);
    }

    // 查找包
    mp_obj_dict_t *data_dict = MP_OBJ_TO_PTR(self->data);
    mp_map_elem_t *pkg_elem = mp_map_lookup(&data_dict->map, name_obj, MP_MAP_LOOKUP);

    if (pkg_elem == NULL) {
        return mp_const_none;
    }

    // 查找版本
    mp_obj_dict_t *version_dict = MP_OBJ_TO_PTR(pkg_elem->value);
    mp_map_elem_t *ver_elem = mp_map_lookup(&version_dict->map, version_obj, MP_MAP_LOOKUP);

    if (ver_elem == NULL) {
        return mp_const_none;
    }

    return ver_elem->value;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_registry_get_package_obj, refun_registry_get_package);

// ============================================================================
// Registry.list_versions(name) - 列出包的所有版本
// ============================================================================

static mp_obj_t refun_registry_list_versions(mp_obj_t self_in, mp_obj_t name_obj) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 确保已加载
    if (!self->loaded) {
        refun_registry_load(self_in);
    }

    // 查找包
    mp_obj_dict_t *data_dict = MP_OBJ_TO_PTR(self->data);
    mp_map_elem_t *pkg_elem = mp_map_lookup(&data_dict->map, name_obj, MP_MAP_LOOKUP);

    if (pkg_elem == NULL) {
        return mp_obj_new_list(0, NULL);
    }

    // 创建版本列表
    mp_obj_dict_t *version_dict = MP_OBJ_TO_PTR(pkg_elem->value);
    mp_obj_t versions = mp_obj_new_list(0, NULL);

    for (size_t i = 0; i < version_dict->map.alloc; i++) {
        if (mp_map_slot_is_filled(&version_dict->map, i)) {
            mp_obj_list_append(versions, version_dict->map.table[i].key);
        }
    }

    return versions;
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_registry_list_versions_obj, refun_registry_list_versions);

// ============================================================================
// Registry.is_installed(name, version) - 检查包是否已安装
// ============================================================================

static mp_obj_t refun_registry_is_installed(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    mp_obj_t metadata = refun_registry_get_package(self_in, name_obj, version_obj);
    return mp_obj_new_bool(metadata != mp_const_none);
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_registry_is_installed_obj, refun_registry_is_installed);

// ============================================================================
// Registry.get_all_packages() - 获取所有包
// ============================================================================

static mp_obj_t refun_registry_get_all_packages(mp_obj_t self_in) {
    refun_registry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 确保已加载
    if (!self->loaded) {
        refun_registry_load(self_in);
    }

    return self->data;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_registry_get_all_packages_obj, refun_registry_get_all_packages);

// ============================================================================
// Registry 类型的本地字典（方法表）
// ============================================================================

static const mp_rom_map_elem_t refun_registry_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_load), MP_ROM_PTR(&refun_registry_load_obj) },
    { MP_ROM_QSTR(MP_QSTR_save), MP_ROM_PTR(&refun_registry_save_obj) },
    { MP_ROM_QSTR(MP_QSTR_add_package), MP_ROM_PTR(&refun_registry_add_package_obj) },
    { MP_ROM_QSTR(MP_QSTR_remove_package), MP_ROM_PTR(&refun_registry_remove_package_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_package), MP_ROM_PTR(&refun_registry_get_package_obj) },
    { MP_ROM_QSTR(MP_QSTR_list_versions), MP_ROM_PTR(&refun_registry_list_versions_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_installed), MP_ROM_PTR(&refun_registry_is_installed_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_all_packages), MP_ROM_PTR(&refun_registry_get_all_packages_obj) },
};
static MP_DEFINE_CONST_DICT(refun_registry_locals_dict, refun_registry_locals_dict_table);

// ============================================================================
// Registry 类型定义
// ============================================================================

MP_DEFINE_CONST_OBJ_TYPE(
    refun_registry_type,
    MP_QSTR_Registry,
    MP_TYPE_FLAG_NONE,
    make_new, refun_registry_make_new,
    locals_dict, &refun_registry_locals_dict
);
