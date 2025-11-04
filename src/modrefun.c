// modrefun.c - reFun 包管理器 C 模块入口
// ESP32S3 的 MicroPython 用户 C 模块

#include "py/obj.h"
#include "py/runtime.h"
#include "py/builtin.h"

#include "refun_version.h"
#include "refun_resolver.h"
#include "refun_utils.h"
#include "refun_registry.h"
#include "refun_fetcher.h"
#include "refun_patcher.h"
#include "refun_loader.h"
#include "refun_manager.h"

// 模块版本字符串
#define REFUN_VERSION "1.0.0-c"

// 模块函数前向声明
static mp_obj_t refun_version_string(void) {
    return mp_obj_new_str(REFUN_VERSION, strlen(REFUN_VERSION));
}
static MP_DEFINE_CONST_FUN_OBJ_0(refun_version_string_obj, refun_version_string);

// 模块全局符号表
static const mp_rom_map_elem_t refun_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_refun) },
    { MP_ROM_QSTR(MP_QSTR___version__), MP_ROM_PTR(&refun_version_string_obj) },

    // 版本管理
    { MP_ROM_QSTR(MP_QSTR_Version), MP_ROM_PTR(&refun_version_type) },
    { MP_ROM_QSTR(MP_QSTR_Constraint), MP_ROM_PTR(&refun_constraint_type) },

    // 依赖解析
    { MP_ROM_QSTR(MP_QSTR_DependencyResolver), MP_ROM_PTR(&refun_resolver_type) },
    { MP_ROM_QSTR(MP_QSTR_topological_sort), MP_ROM_PTR(&refun_topological_sort_obj) },
    { MP_ROM_QSTR(MP_QSTR_detect_circular_dep), MP_ROM_PTR(&refun_detect_circular_dep_obj) },
    { MP_ROM_QSTR(MP_QSTR_match_version), MP_ROM_PTR(&refun_match_version_obj) },

    // 工具函数
    { MP_ROM_QSTR(MP_QSTR_path_join), MP_ROM_PTR(&refun_path_join_obj) },
    { MP_ROM_QSTR(MP_QSTR_normalize_path), MP_ROM_PTR(&refun_normalize_path_obj) },
    { MP_ROM_QSTR(MP_QSTR_hash_string), MP_ROM_PTR(&refun_hash_string_obj) },

    // 包管理器类（阶段3新增）
    { MP_ROM_QSTR(MP_QSTR_Registry), MP_ROM_PTR(&refun_registry_type) },
    { MP_ROM_QSTR(MP_QSTR_Fetcher), MP_ROM_PTR(&refun_fetcher_type) },
    { MP_ROM_QSTR(MP_QSTR_PatchManager), MP_ROM_PTR(&refun_patcher_type) },
    { MP_ROM_QSTR(MP_QSTR_PackageLoader), MP_ROM_PTR(&refun_loader_type) },
    { MP_ROM_QSTR(MP_QSTR_PackageManager), MP_ROM_PTR(&refun_manager_type) },
};
static MP_DEFINE_CONST_DICT(refun_module_globals, refun_module_globals_table);

// 模块定义
const mp_obj_module_t refun_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&refun_module_globals,
};

// 注册模块
// MicroPython 1.24+ 使用 MP_REGISTER_MODULE
#if MICROPY_VERSION >= MICROPY_MAKE_VERSION(1, 24, 0)
MP_REGISTER_MODULE(MP_QSTR_refun, refun_user_cmodule);
#else
MP_REGISTER_MODULE(MP_QSTR_refun, refun_user_cmodule, MODULE_REFUN_ENABLED);
#endif
