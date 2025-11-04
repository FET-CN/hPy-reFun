// refun_manager.c - reFun 包管理器的统一高层 API 实现
// 提供用户友好的包管理接口

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "refun_manager.h"
#include "refun_registry.h"
#include "refun_fetcher.h"
#include "refun_patcher.h"
#include "refun_loader.h"
#include "refun_utils.h"

#include <string.h>

// ============================================================================
// 内部辅助函数：确保目录存在
// ============================================================================

static void ensure_directory_exists(mp_obj_t dir_path) {
    nlr_buf_t nlr;

    if (nlr_push(&nlr) == 0) {
        mp_obj_t os_module = mp_import_name(MP_QSTR_os, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t makedirs_func = mp_load_attr(os_module, MP_QSTR_makedirs);
        mp_call_function_1(makedirs_func, dir_path);
        nlr_pop();
    } else {
        // 忽略已存在错误
    }
}

// ============================================================================
// PackageManager 构造函数
// ============================================================================

static mp_obj_t refun_manager_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    // 解析参数
    enum { ARG_storage_path, ARG_packages_path };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_storage_path, MP_ARG_OBJ, {.u_obj = MP_OBJ_NEW_QSTR(MP_QSTR_storage)} },
        { MP_QSTR_packages_path, MP_ARG_OBJ, {.u_obj = MP_OBJ_NEW_QSTR(MP_QSTR_packages)} },
    };

    mp_arg_val_t arg_vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, 0, args, MP_ARRAY_SIZE(allowed_args), allowed_args, arg_vals);

    // 创建 PackageManager 对象
    refun_manager_obj_t *self = mp_obj_malloc(refun_manager_obj_t, type);

    // 保存路径
    self->storage_path = arg_vals[ARG_storage_path].u_obj;
    self->packages_path = arg_vals[ARG_packages_path].u_obj;

    // 确保目录存在
    ensure_directory_exists(self->storage_path);
    ensure_directory_exists(self->packages_path);

    // 创建子模块

    // Registry
    mp_obj_t registry_path_parts[2] = {self->storage_path, MP_OBJ_NEW_QSTR(MP_QSTR_registry_dot_json)};
    mp_obj_t registry_path = refun_path_join(2, registry_path_parts);
    mp_obj_t registry_args[1] = {registry_path};
    self->registry = refun_registry_make_new(&refun_registry_type, 1, 0, registry_args);

    // Fetcher
    mp_obj_t objects_path_parts[2] = {self->storage_path, MP_OBJ_NEW_QSTR(MP_QSTR_objects)};
    mp_obj_t objects_path = refun_path_join(2, objects_path_parts);
    mp_obj_t fetcher_args[1] = {objects_path};
    self->fetcher = refun_fetcher_make_new(&refun_fetcher_type, 1, 0, fetcher_args);

    // PatchManager
    self->patcher = refun_patcher_make_new(&refun_patcher_type, 0, 0, NULL);

    // DependencyResolver (暂时为 None，需要实现)
    self->resolver = mp_const_none;

    // PackageLoader
    mp_obj_t loader_args[4] = {self->registry, self->resolver, self->patcher, self->fetcher};
    self->loader = refun_loader_make_new(&refun_loader_type, 4, 0, loader_args);

    // 加载注册表
    mp_obj_t load_method = mp_load_attr(self->registry, MP_QSTR_load);
    mp_call_function_0(load_method);

    return MP_OBJ_FROM_PTR(self);
}

// ============================================================================
// PackageManager.install_local(name, version, pkg_path) - 从本地安装包
// ============================================================================

static mp_obj_t refun_manager_install_local(size_t n_args, const mp_obj_t *args) {
    refun_manager_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name_obj = args[1];
    mp_obj_t version_obj = args[2];
    mp_obj_t pkg_path_obj = args[3];

    // TODO: 计算包内容 Hash（简化实现，使用固定哈希）
    mp_obj_t hash_obj = MP_OBJ_NEW_QSTR(MP_QSTR_dummy_hash);

    // 存储到对象池
    mp_obj_t store_file_method = mp_load_attr(self->fetcher, MP_QSTR_store_file);

    nlr_buf_t nlr;
    mp_obj_t obj_path = mp_const_none;

    if (nlr_push(&nlr) == 0) {
        obj_path = mp_call_function_2(store_file_method, pkg_path_obj, hash_obj);
        nlr_pop();
    } else {
        // 如果存储失败，使用原路径
        obj_path = pkg_path_obj;
    }

    // 创建元数据
    mp_obj_t metadata = mp_obj_new_dict(0);
    mp_obj_dict_store(metadata, MP_OBJ_NEW_QSTR(MP_QSTR_path), pkg_path_obj);
    mp_obj_dict_store(metadata, MP_OBJ_NEW_QSTR(MP_QSTR_hash), hash_obj);
    mp_obj_dict_store(metadata, MP_OBJ_NEW_QSTR(MP_QSTR_deps), mp_obj_new_dict(0));

    // 注册到 registry
    mp_obj_t add_package_method = mp_load_attr(self->registry, MP_QSTR_add_package);
    mp_obj_t add_args[4] = {self->registry, name_obj, version_obj, metadata};
    mp_call_function_n_kw(add_package_method, 3, 0, add_args + 1);

    // 保存 registry
    mp_obj_t save_method = mp_load_attr(self->registry, MP_QSTR_save);
    mp_call_function_0(save_method);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_manager_install_local_obj, 4, 4, refun_manager_install_local);

// ============================================================================
// PackageManager.uninstall(name, version) - 卸载包
// ============================================================================

static mp_obj_t refun_manager_uninstall(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj) {
    refun_manager_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 从 registry 移除
    mp_obj_t remove_package_method = mp_load_attr(self->registry, MP_QSTR_remove_package);
    mp_call_function_2(remove_package_method, name_obj, version_obj);

    // 保存 registry
    mp_obj_t save_method = mp_load_attr(self->registry, MP_QSTR_save);
    mp_call_function_0(save_method);

    // TODO: 可选删除对象文件

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_manager_uninstall_obj, refun_manager_uninstall);

// ============================================================================
// PackageManager.load(name, version=None) - 加载包
// ============================================================================

static mp_obj_t refun_manager_load(size_t n_args, const mp_obj_t *args) {
    refun_manager_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name_obj = args[1];
    mp_obj_t version_obj = (n_args > 2) ? args[2] : mp_const_none;

    // 委托给 loader
    mp_obj_t load_method = mp_load_attr(self->loader, MP_QSTR_load);

    if (version_obj == mp_const_none) {
        return mp_call_function_1(load_method, name_obj);
    } else {
        return mp_call_function_2(load_method, name_obj, version_obj);
    }
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(refun_manager_load_obj, 2, 3, refun_manager_load);

// ============================================================================
// PackageManager.list_installed() - 列出已安装的包
// ============================================================================

static mp_obj_t refun_manager_list_installed(mp_obj_t self_in) {
    refun_manager_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 获取所有包
    mp_obj_t get_all_method = mp_load_attr(self->registry, MP_QSTR_get_all_packages);
    mp_obj_t all_packages = mp_call_function_0(get_all_method);

    // 创建结果列表
    mp_obj_t result = mp_obj_new_list(0, NULL);

    // 遍历所有包和版本
    mp_obj_dict_t *packages_dict = MP_OBJ_TO_PTR(all_packages);
    for (size_t i = 0; i < packages_dict->map.alloc; i++) {
        if (mp_map_slot_is_filled(&packages_dict->map, i)) {
            mp_obj_t pkg_name = packages_dict->map.table[i].key;
            mp_obj_dict_t *versions_dict = MP_OBJ_TO_PTR(packages_dict->map.table[i].value);

            for (size_t j = 0; j < versions_dict->map.alloc; j++) {
                if (mp_map_slot_is_filled(&versions_dict->map, j)) {
                    mp_obj_t version = versions_dict->map.table[j].key;
                    mp_obj_t tuple[2] = {pkg_name, version};
                    mp_obj_list_append(result, mp_obj_new_tuple(2, tuple));
                }
            }
        }
    }

    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_manager_list_installed_obj, refun_manager_list_installed);

// ============================================================================
// PackageManager.list_loaded() - 列出已加载的包
// ============================================================================

static mp_obj_t refun_manager_list_loaded(mp_obj_t self_in) {
    refun_manager_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 获取 loader 的缓存
    refun_loader_obj_t *loader = MP_OBJ_TO_PTR(self->loader);
    mp_obj_t loaded_cache = loader->loaded_cache;

    // 创建结果列表
    mp_obj_t result = mp_obj_new_list(0, NULL);

    // 遍历缓存
    mp_obj_dict_t *cache_dict = MP_OBJ_TO_PTR(loaded_cache);
    for (size_t i = 0; i < cache_dict->map.alloc; i++) {
        if (mp_map_slot_is_filled(&cache_dict->map, i)) {
            mp_obj_list_append(result, cache_dict->map.table[i].key);
        }
    }

    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_manager_list_loaded_obj, refun_manager_list_loaded);

// ============================================================================
// PackageManager 类型的本地字典（方法表）
// ============================================================================

static const mp_rom_map_elem_t refun_manager_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_install_local), MP_ROM_PTR(&refun_manager_install_local_obj) },
    { MP_ROM_QSTR(MP_QSTR_uninstall), MP_ROM_PTR(&refun_manager_uninstall_obj) },
    { MP_ROM_QSTR(MP_QSTR_load), MP_ROM_PTR(&refun_manager_load_obj) },
    { MP_ROM_QSTR(MP_QSTR_list_installed), MP_ROM_PTR(&refun_manager_list_installed_obj) },
    { MP_ROM_QSTR(MP_QSTR_list_loaded), MP_ROM_PTR(&refun_manager_list_loaded_obj) },
};
static MP_DEFINE_CONST_DICT(refun_manager_locals_dict, refun_manager_locals_dict_table);

// ============================================================================
// PackageManager 类型定义
// ============================================================================

MP_DEFINE_CONST_OBJ_TYPE(
    refun_manager_type,
    MP_QSTR_PackageManager,
    MP_TYPE_FLAG_NONE,
    make_new, refun_manager_make_new,
    locals_dict, &refun_manager_locals_dict
);
