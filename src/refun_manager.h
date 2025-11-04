// refun_manager.h - reFun 包管理器的统一高层 API
// 提供用户友好的包管理接口

#ifndef REFUN_MANAGER_H
#define REFUN_MANAGER_H

#include "py/obj.h"
#include "py/runtime.h"

// PackageManager 对象结构
typedef struct {
    mp_obj_base_t base;
    mp_obj_t storage_path;   // 存储根目录（字符串）
    mp_obj_t packages_path;  // 包目录（字符串）
    mp_obj_t registry;       // Registry 对象
    mp_obj_t fetcher;        // Fetcher 对象
    mp_obj_t patcher;        // PatchManager 对象
    mp_obj_t resolver;       // DependencyResolver 对象
    mp_obj_t loader;         // PackageLoader 对象
} refun_manager_obj_t;

// 类型声明
extern const mp_obj_type_t refun_manager_type;

// PackageManager API 函数
mp_obj_t refun_manager_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

// PackageManager 方法
mp_obj_t refun_manager_install_local(size_t n_args, const mp_obj_t *args);
mp_obj_t refun_manager_uninstall(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);
mp_obj_t refun_manager_load(size_t n_args, const mp_obj_t *args);
mp_obj_t refun_manager_list_installed(mp_obj_t self_in);
mp_obj_t refun_manager_list_loaded(mp_obj_t self_in);

#endif // REFUN_MANAGER_H
