// refun_patcher.h - reFun 包管理器的 Monkey Patch 管理
// 提供动态修改模块功能的能力

#ifndef REFUN_PATCHER_H
#define REFUN_PATCHER_H

#include "py/obj.h"
#include "py/runtime.h"

// PatchManager 对象结构
typedef struct {
    mp_obj_base_t base;
    mp_obj_t patches;  // dict: {target_module: [patch_funcs]}
} refun_patcher_obj_t;

// 类型声明
extern const mp_obj_type_t refun_patcher_type;

// PatchManager API 函数
mp_obj_t refun_patcher_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

// PatchManager 方法
mp_obj_t refun_patcher_register_patch(mp_obj_t self_in, mp_obj_t target_module_obj, mp_obj_t patch_func_obj);
mp_obj_t refun_patcher_apply_patches(mp_obj_t self_in, mp_obj_t module_obj);
mp_obj_t refun_patcher_load_patch_module(mp_obj_t self_in, mp_obj_t patch_module_path_obj);
mp_obj_t refun_patcher_get_patches(mp_obj_t self_in, mp_obj_t target_obj);

#endif // REFUN_PATCHER_H
