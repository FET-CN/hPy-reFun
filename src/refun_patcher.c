// refun_patcher.c - reFun 包管理器的 Monkey Patch 管理实现
// 提供动态修改模块功能的能力

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objdict.h"
#include "refun_patcher.h"

#include <string.h>

// ============================================================================
// PatchManager 构造函数
// ============================================================================

static mp_obj_t refun_patcher_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    // 创建 PatchManager 对象
    refun_patcher_obj_t *self = mp_obj_malloc(refun_patcher_obj_t, type);

    // 初始化 patches 字典
    self->patches = mp_obj_new_dict(0);

    return MP_OBJ_FROM_PTR(self);
}

// ============================================================================
// PatchManager.register_patch(target_module, patch_func) - 注册 patch
// ============================================================================

static mp_obj_t refun_patcher_register_patch(mp_obj_t self_in, mp_obj_t target_module_obj, mp_obj_t patch_func_obj) {
    refun_patcher_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 检查 patch_func 是否可调用
    if (!mp_obj_is_callable(patch_func_obj)) {
        mp_raise_TypeError(MP_ERROR_TEXT("patch_func must be callable"));
    }

    // 获取或创建目标模块的 patch 列表
    mp_obj_dict_t *patches_dict = MP_OBJ_TO_PTR(self->patches);
    mp_map_elem_t *elem = mp_map_lookup(&patches_dict->map, target_module_obj, MP_MAP_LOOKUP_ADD_IF_MISSING);

    if (elem->value == MP_OBJ_NULL) {
        // 创建新的 patch 列表
        elem->value = mp_obj_new_list(0, NULL);
    }

    // 添加 patch 函数到列表
    mp_obj_list_append(elem->value, patch_func_obj);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(refun_patcher_register_patch_obj, refun_patcher_register_patch);

// ============================================================================
// PatchManager.apply_patches(module_obj) - 应用 patches
// ============================================================================

static mp_obj_t refun_patcher_apply_patches(mp_obj_t self_in, mp_obj_t module_obj) {
    refun_patcher_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 获取模块名称
    mp_obj_t module_name = mp_load_attr(module_obj, MP_QSTR___name__);

    // 查找该模块的 patch 列表
    mp_obj_dict_t *patches_dict = MP_OBJ_TO_PTR(self->patches);
    mp_map_elem_t *elem = mp_map_lookup(&patches_dict->map, module_name, MP_MAP_LOOKUP);

    if (elem == NULL) {
        // 没有 patch，直接返回
        return mp_const_none;
    }

    // 遍历 patch 列表并应用
    mp_obj_t patch_list = elem->value;
    size_t len = mp_obj_get_int(mp_obj_len(patch_list));

    for (size_t i = 0; i < len; i++) {
        mp_obj_t patch_func = mp_obj_list_get(patch_list, i);
        // 调用 patch(target_module)
        mp_call_function_1(patch_func, module_obj);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_patcher_apply_patches_obj, refun_patcher_apply_patches);

// ============================================================================
// PatchManager.load_patch_module(patch_module_path) - 加载 __patch__.py
// ============================================================================

static mp_obj_t refun_patcher_load_patch_module(mp_obj_t self_in, mp_obj_t patch_module_path_obj) {
    refun_patcher_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 读取并执行 patch 模块文件
    // 打开文件
    mp_obj_t args[2] = {patch_module_path_obj, MP_OBJ_NEW_QSTR(MP_QSTR_r)};
    mp_obj_t file_obj = mp_builtin_open(2, args, (mp_map_t *)&mp_const_empty_map);

    // 读取文件内容
    int errcode;
    mp_uint_t file_size = mp_stream_posix_lseek((mp_obj_t)file_obj, 0, SEEK_END, &errcode);
    mp_stream_posix_lseek((mp_obj_t)file_obj, 0, SEEK_SET, &errcode);

    vstr_t vstr;
    vstr_init_len(&vstr, file_size);
    mp_stream_read_exactly((mp_obj_t)file_obj, vstr.buf, file_size, &errcode);

    // 关闭文件
    mp_stream_close(file_obj);

    // 创建一个临时模块命名空间
    mp_obj_t module_dict = mp_obj_new_dict(0);

    // 添加特殊属性
    mp_obj_dict_store(module_dict, MP_OBJ_NEW_QSTR(MP_QSTR___name__), MP_OBJ_NEW_QSTR(MP_QSTR___patch__));
    mp_obj_dict_store(module_dict, MP_OBJ_NEW_QSTR(MP_QSTR_register_patch),
                      mp_make_closure_from_proto_fun(
                          MP_OBJ_FROM_PTR(&refun_patcher_register_patch_obj),
                          MP_OBJ_FROM_PTR(self), NULL));

    // 编译并执行代码
    const char *source = vstr_null_terminated_str(&vstr);
    mp_lexer_t *lex = mp_lexer_new_from_str_len(MP_QSTR___patch__, source, strlen(source), false);
    mp_parse_tree_t parse_tree = mp_parse(lex, MP_PARSE_FILE_INPUT);
    mp_obj_t module_fun = mp_compile(&parse_tree, MP_QSTR___patch__, false);

    // 在模块字典上下文中执行
    mp_obj_dict_t *old_globals = mp_globals_get();
    mp_globals_set(MP_OBJ_TO_PTR(module_dict));
    mp_call_function_0(module_fun);
    mp_globals_set(old_globals);

    vstr_clear(&vstr);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_patcher_load_patch_module_obj, refun_patcher_load_patch_module);

// ============================================================================
// PatchManager.get_patches(target) - 获取某模块的 patches
// ============================================================================

static mp_obj_t refun_patcher_get_patches(mp_obj_t self_in, mp_obj_t target_obj) {
    refun_patcher_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // 查找该模块的 patch 列表
    mp_obj_dict_t *patches_dict = MP_OBJ_TO_PTR(self->patches);
    mp_map_elem_t *elem = mp_map_lookup(&patches_dict->map, target_obj, MP_MAP_LOOKUP);

    if (elem == NULL) {
        return mp_obj_new_list(0, NULL);
    }

    return elem->value;
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_patcher_get_patches_obj, refun_patcher_get_patches);

// ============================================================================
// PatchManager 类型的本地字典（方法表）
// ============================================================================

static const mp_rom_map_elem_t refun_patcher_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_register_patch), MP_ROM_PTR(&refun_patcher_register_patch_obj) },
    { MP_ROM_QSTR(MP_QSTR_apply_patches), MP_ROM_PTR(&refun_patcher_apply_patches_obj) },
    { MP_ROM_QSTR(MP_QSTR_load_patch_module), MP_ROM_PTR(&refun_patcher_load_patch_module_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_patches), MP_ROM_PTR(&refun_patcher_get_patches_obj) },
};
static MP_DEFINE_CONST_DICT(refun_patcher_locals_dict, refun_patcher_locals_dict_table);

// ============================================================================
// PatchManager 类型定义
// ============================================================================

MP_DEFINE_CONST_OBJ_TYPE(
    refun_patcher_type,
    MP_QSTR_PatchManager,
    MP_TYPE_FLAG_NONE,
    make_new, refun_patcher_make_new,
    locals_dict, &refun_patcher_locals_dict
);
