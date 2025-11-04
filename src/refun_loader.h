// refun_loader.h - reFun 包管理器的动态模块加载
// 提供包的动态导入和依赖加载功能

#ifndef REFUN_LOADER_H
#define REFUN_LOADER_H

#include "py/obj.h"
#include "py/runtime.h"

// PackageLoader 对象结构
typedef struct {
    mp_obj_base_t base;
    mp_obj_t registry;       // Registry 对象引用
    mp_obj_t resolver;       // DependencyResolver 对象引用
    mp_obj_t patcher;        // PatchManager 对象引用
    mp_obj_t fetcher;        // Fetcher 对象引用
    mp_obj_t loaded_cache;   // dict: {(name, version): module}
} refun_loader_obj_t;

// 类型声明
extern const mp_obj_type_t refun_loader_type;

// PackageLoader API 函数
mp_obj_t refun_loader_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

// PackageLoader 方法
mp_obj_t refun_loader_load(size_t n_args, const mp_obj_t *args);
mp_obj_t refun_loader_unload(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);
mp_obj_t refun_loader_is_loaded(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);

#endif // REFUN_LOADER_H
