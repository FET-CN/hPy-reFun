// refun_loader.c - reFun 包管理器的动态模块加载实现
// 提供包的动态导入和依赖加载功能

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objdict.h"
#include "refun_loader.h"

#include <string.h>

// ============================================================================
// PackageLoader 构造函数
// ============================================================================

static mp_obj_t refun_loader_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 4, 4, false);

    // 创建 PackageLoader 对象
    refun_loader_obj_t *self = mp_obj_malloc(refun_loader_obj_t, type);

    // 保存依赖对象
    self->registry = args[0];
    self->resolver = args[1];
    self->patcher = args[2];
    self->fetcher = args[3];

    // 初始化缓存
    self->loaded_cache = mp_obj_new_dict(0);

    return MP_OBJ_FROM_PTR(self);
}

// ============================================================================
// 内部辅助函数：生成缓存键 (name, version)
// ============================================================================

static mp_obj_t make_cache_key(mp_obj_t name_obj, mp_obj_t version_obj) {
    mp_obj_t tuple[2] = {name_obj, version_obj};
    return mp_obj_new_tuple(2, tuple);
}

// ============================================================================
// 内部辅助函数：添加路径到 sys.path
// ============================================================================

static void add_to_sys_path(mp_obj_t path_obj) {
    // 获取 sys 模块
    mp_obj_t sys_module = mp_import_name(MP_QSTR_sys, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t sys_path = mp_load_attr(sys_module, MP_QSTR_path);

    // 检查路径是否已存在
    mp_obj_t iter = mp_getiter(sys_path, NULL);
    mp_obj_t item;
    while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
        if (mp_obj_equal(item, path_obj)) {
            return; // 已存在
        }
    }

    // 添加到 sys.path
    mp_obj_list_append(sys_path, path_obj);
}

// ============================================================================
// 内部辅助函数：从 sys.path 移除路径
// ============================================================================

static void remove_from_sys_path(mp_obj_t path_obj) {
    // 获取 sys 模块
    mp_obj_t sys_module = mp_import_name(MP_QSTR_sys, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t sys_path = mp_load_attr(sys_module, MP_QSTR_path);

    // 移除路径（使用 list.remove）
    mp_obj_t remove_method = mp_load_attr(sys_path, MP_QSTR_remove);

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_call_function_1(remove_method, path_obj);
        nlr_pop();
    } else {
        // 忽略错误（路径不存在）
    }
}

// ============================================================================
// PackageLoader.is_loaded(name, version) - 检查是否已加载
// ============================================================================

static mp_obj_t refun_loader_is_loaded(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    refun_loader_obj_t *self = MP_OBJ_TO_PTR(self_in);

    mp_obj_t cache_key = make_cache_key(name_obj, version_obj);
    mp_obj_dict_t *cache_dict = MP_OBJ_TO_PTR(self->loaded_cache);
    mp_map_elem_t *elem = mp_map_lookup(&cache_dict->map, cache_key, MP_MAP_LOOKUP);

    return mp_obj_new_bool(elem != NULL);
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_loader_is_loaded_obj, refun_loader_is_loaded);

// ============================================================================
// PackageLoader.load(name, version=None) - 加载包
// ============================================================================

static mp_obj_t refun_loader_load(size_t n_args, const mp_obj_t *args) {
    refun_loader_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name_obj = args[1];
    mp_obj_t version_obj = (n_args > 2) ? args[2] : mp_const_none;

    // 检查缓存
    if (version_obj != mp_const_none) {
        mp_obj_t cache_key = make_cache_key(name_obj, version_obj);
        mp_obj_dict_t *cache_dict = MP_OBJ_TO_PTR(self->loaded_cache);
        mp_map_elem_t *elem = mp_map_lookup(&cache_dict->map, cache_key, MP_MAP_LOOKUP);

        if (elem != NULL) {
            return elem->value; // 已加载，返回缓存
        }
    }

    // 如果没有指定版本，从 registry 获取最新版本
    if (version_obj == mp_const_none) {
        // 调用 registry.list_versions(name)
        mp_obj_t list_versions_method = mp_load_attr(self->registry, MP_QSTR_list_versions);
        mp_obj_t versions = mp_call_function_1(list_versions_method, name_obj);

        // 获取最后一个版本（最高版本）
        size_t len = mp_obj_get_int(mp_obj_len(versions));
        if (len == 0) {
            mp_raise_msg_varg(&mp_type_ValueError,
                MP_ERROR_TEXT("Package '%s' not found"), mp_obj_str_get_str(name_obj));
        }
        version_obj = mp_obj_list_get(versions, len - 1);
    }

    // 获取包元数据
    mp_obj_t get_package_method = mp_load_attr(self->registry, MP_QSTR_get_package);
    mp_obj_t metadata = mp_call_function_2(get_package_method, name_obj, version_obj);

    if (metadata == mp_const_none) {
        mp_raise_msg_varg(&mp_type_ValueError,
            MP_ERROR_TEXT("Package '%s@%s' not found"),
            mp_obj_str_get_str(name_obj),
            mp_obj_str_get_str(version_obj));
    }

    // 获取包路径
    mp_obj_t path_obj = mp_obj_dict_get(metadata, MP_OBJ_NEW_QSTR(MP_QSTR_path));

    // TODO: 解析并加载依赖（需要 DependencyResolver）
    // 当前简化实现：直接加载主包

    // 添加到 sys.path
    add_to_sys_path(path_obj);

    // 动态导入模块
    const char *name_str = mp_obj_str_get_str(name_obj);
    qstr name_qstr = qstr_from_str(name_str);
    mp_obj_t module = mp_builtin___import__(1, &MP_OBJ_NEW_QSTR(name_qstr));

    // 应用 patches（如果有）
    mp_obj_t apply_patches_method = mp_load_attr(self->patcher, MP_QSTR_apply_patches);
    mp_call_function_1(apply_patches_method, module);

    // 缓存结果
    mp_obj_t cache_key = make_cache_key(name_obj, version_obj);
    mp_obj_dict_store(self->loaded_cache, cache_key, module);

    return module;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_loader_load_obj, 2, 3, refun_loader_load);

// ============================================================================
// PackageLoader.unload(name, version) - 卸载包
// ============================================================================

static mp_obj_t refun_loader_unload(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    refun_loader_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 获取包元数据
    mp_obj_t get_package_method = mp_load_attr(self->registry, MP_QSTR_get_package);
    mp_obj_t metadata = mp_call_function_2(get_package_method, name_obj, version_obj);

    if (metadata != mp_const_none) {
        // 获取包路径并从 sys.path 移除
        mp_obj_t path_obj = mp_obj_dict_get(metadata, MP_OBJ_NEW_QSTR(MP_QSTR_path));
        remove_from_sys_path(path_obj);
    }

    // 从 sys.modules 移除
    mp_obj_t sys_module = mp_import_name(MP_QSTR_sys, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t sys_modules = mp_load_attr(sys_module, MP_QSTR_modules);

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_obj_dict_delete(sys_modules, name_obj);
        nlr_pop();
    } else {
        // 忽略错误（模块不存在）
    }

    // 清除缓存
    mp_obj_t cache_key = make_cache_key(name_obj, version_obj);
    mp_obj_dict_t *cache_dict = MP_OBJ_TO_PTR(self->loaded_cache);
    mp_map_lookup(&cache_dict->map, cache_key, MP_MAP_LOOKUP_REMOVE_IF_FOUND);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_loader_unload_obj, refun_loader_unload);

// ============================================================================
// PackageLoader 类型的本地字典（方法表）
// ============================================================================

static const mp_rom_map_elem_t refun_loader_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_load), MP_ROM_PTR(&refun_loader_load_obj) },
    { MP_ROM_QSTR(MP_QSTR_unload), MP_ROM_PTR(&refun_loader_unload_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_loaded), MP_ROM_PTR(&refun_loader_is_loaded_obj) },
};
static MP_DEFINE_CONST_DICT(refun_loader_locals_dict, refun_loader_locals_dict_table);

// ============================================================================
// PackageLoader 类型定义
// ============================================================================

MP_DEFINE_CONST_OBJ_TYPE(
    refun_loader_type,
    MP_QSTR_PackageLoader,
    MP_TYPE_FLAG_NONE,
    make_new, refun_loader_make_new,
    locals_dict, &refun_loader_locals_dict
);
