// refun_version.h - reFun 包管理器的版本管理
// 提供快速的版本比较和约束匹配

#ifndef REFUN_VERSION_H
#define REFUN_VERSION_H

#include "py/obj.h"
#include "py/runtime.h"

// 版本约束操作符
typedef enum {
    CONSTRAINT_OP_EQ,      // ==
    CONSTRAINT_OP_GTE,     // >=
    CONSTRAINT_OP_GT,      // >
    CONSTRAINT_OP_LTE,     // <=
    CONSTRAINT_OP_LT,      // <
    CONSTRAINT_OP_CARET,   // ^ (兼容版本)
    CONSTRAINT_OP_TILDE    // ~ (近似等效)
} constraint_op_t;

// 版本对象结构
typedef struct {
    mp_obj_base_t base;
    uint16_t major;
    uint16_t minor;
    uint16_t patch;
    mp_obj_t prerelease;  // 字符串或 None
} refun_version_obj_t;

// 约束对象结构
typedef struct {
    mp_obj_base_t base;
    constraint_op_t op;
    refun_version_obj_t *version;
} refun_constraint_obj_t;

// 类型声明
extern const mp_obj_type_t refun_version_type;
extern const mp_obj_type_t refun_constraint_type;

// 版本 API 函数
mp_obj_t refun_version_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t refun_version_parse(mp_obj_t str_obj);
int refun_version_compare(refun_version_obj_t *v1, refun_version_obj_t *v2);

// 约束 API 函数
mp_obj_t refun_constraint_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t refun_constraint_parse(mp_obj_t str_obj);
bool refun_constraint_matches(refun_constraint_obj_t *constraint, refun_version_obj_t *version);

#endif // REFUN_VERSION_H
