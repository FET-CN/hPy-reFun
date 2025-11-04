// refun_registry.h - reFun 包管理器的注册表管理
// 提供包的注册、查询和持久化功能

#ifndef REFUN_REGISTRY_H
#define REFUN_REGISTRY_H

#include "py/obj.h"
#include "py/runtime.h"

// Registry 对象结构
typedef struct {
    mp_obj_base_t base;
    mp_obj_t registry_path;  // 注册表文件路径（字符串）
    mp_obj_t data;           // dict: {name: {version: metadata}}
    bool dirty;              // 数据是否已修改（需要保存）
    bool loaded;             // 是否已从文件加载
} refun_registry_obj_t;

// 类型声明
extern const mp_obj_type_t refun_registry_type;

// Registry API 函数
mp_obj_t refun_registry_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

// Registry 方法
mp_obj_t refun_registry_load(mp_obj_t self_in);
mp_obj_t refun_registry_save(mp_obj_t self_in);
mp_obj_t refun_registry_add_package(size_t n_args, const mp_obj_t *args);
mp_obj_t refun_registry_remove_package(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);
mp_obj_t refun_registry_get_package(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);
mp_obj_t refun_registry_list_versions(mp_obj_t self_in, mp_obj_t name_obj);
mp_obj_t refun_registry_is_installed(mp_obj_t self_in, mp_obj_t name_obj, mp_obj_t version_obj);
mp_obj_t refun_registry_get_all_packages(mp_obj_t self_in);

#endif // REFUN_REGISTRY_H
