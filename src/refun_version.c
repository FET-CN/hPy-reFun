// refun_version.c - 版本管理实现
// 为 reFun 提供快速的版本比较和约束匹配

#include <string.h>
#include <ctype.h>
#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "refun_version.h"

//=============================================================================
// 版本对象实现
//=============================================================================

// 版本对象打印
static void refun_version_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    refun_version_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->prerelease != mp_const_none) {
        mp_printf(print, "Version(%u.%u.%u-%s)",
                  self->major, self->minor, self->patch,
                  mp_obj_str_get_str(self->prerelease));
    } else {
        mp_printf(print, "Version(%u.%u.%u)",
                  self->major, self->minor, self->patch);
    }
}

// Version.make_new(major, minor, patch, prerelease=None)
mp_obj_t refun_version_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 3, 4, false);

    refun_version_obj_t *self = m_new_obj(refun_version_obj_t);
    self->base.type = &refun_version_type;
    self->major = mp_obj_get_int(args[0]);
    self->minor = mp_obj_get_int(args[1]);
    self->patch = mp_obj_get_int(args[2]);
    self->prerelease = (n_args >= 4) ? args[3] : mp_const_none;

    return MP_OBJ_FROM_PTR(self);
}

// Version.parse("1.2.3-alpha") - 解析版本字符串
mp_obj_t refun_version_parse(mp_obj_t str_obj) {
    const char *str = mp_obj_str_get_str(str_obj);

    uint16_t major = 0, minor = 0, patch = 0;
    const char *prerelease = NULL;

    // 解析 major.minor.patch
    const char *p = str;
    major = 0;
    while (*p && isdigit(*p)) {
        major = major * 10 + (*p - '0');
        p++;
    }
    if (*p != '.') goto parse_error;
    p++;

    minor = 0;
    while (*p && isdigit(*p)) {
        minor = minor * 10 + (*p - '0');
        p++;
    }
    if (*p != '.') goto parse_error;
    p++;

    patch = 0;
    while (*p && isdigit(*p)) {
        patch = patch * 10 + (*p - '0');
        p++;
    }

    // 检查是否有预发布版本
    if (*p == '-') {
        prerelease = p + 1;
    } else if (*p != '\0') {
        goto parse_error;
    }

    // 创建版本对象
    refun_version_obj_t *version = m_new_obj(refun_version_obj_t);
    version->base.type = &refun_version_type;
    version->major = major;
    version->minor = minor;
    version->patch = patch;
    version->prerelease = prerelease ? mp_obj_new_str(prerelease, strlen(prerelease)) : mp_const_none;

    return MP_OBJ_FROM_PTR(version);

parse_error:
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid version string"));
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_version_parse_obj, refun_version_parse);

// 版本比较：返回 -1、0 或 1
int refun_version_compare(refun_version_obj_t *v1, refun_version_obj_t *v2) {
    // 比较 major.minor.patch
    if (v1->major != v2->major) {
        return (v1->major > v2->major) ? 1 : -1;
    }
    if (v1->minor != v2->minor) {
        return (v1->minor > v2->minor) ? 1 : -1;
    }
    if (v1->patch != v2->patch) {
        return (v1->patch > v2->patch) ? 1 : -1;
    }

    // 比较预发布版本
    bool v1_has_pre = (v1->prerelease != mp_const_none);
    bool v2_has_pre = (v2->prerelease != mp_const_none);

    if (!v1_has_pre && !v2_has_pre) return 0;
    if (!v1_has_pre) return 1;  // 正式版 > 预发布版
    if (!v2_has_pre) return -1;

    // 两者都有预发布版本，比较字符串
    return mp_obj_str_get_qstr(v1->prerelease) == mp_obj_str_get_qstr(v2->prerelease) ? 0 :
           (strcmp(mp_obj_str_get_str(v1->prerelease), mp_obj_str_get_str(v2->prerelease)) > 0 ? 1 : -1);
}

// 二元运算
static mp_obj_t refun_version_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (!mp_obj_is_type(rhs_in, &refun_version_type)) {
        return MP_OBJ_NULL; // 不支持此操作
    }

    refun_version_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    refun_version_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
    int cmp = refun_version_compare(lhs, rhs);

    switch (op) {
        case MP_BINARY_OP_EQUAL:
            return mp_obj_new_bool(cmp == 0);
        case MP_BINARY_OP_LESS:
            return mp_obj_new_bool(cmp < 0);
        case MP_BINARY_OP_LESS_EQUAL:
            return mp_obj_new_bool(cmp <= 0);
        case MP_BINARY_OP_MORE:
            return mp_obj_new_bool(cmp > 0);
        case MP_BINARY_OP_MORE_EQUAL:
            return mp_obj_new_bool(cmp >= 0);
        case MP_BINARY_OP_NOT_EQUAL:
            return mp_obj_new_bool(cmp != 0);
        default:
            return MP_OBJ_NULL; // 不支持此操作
    }
}

// Version.to_string() 方法
static mp_obj_t refun_version_to_string(mp_obj_t self_in) {
    refun_version_obj_t *self = MP_OBJ_TO_PTR(self_in);

    char buf[64];
    if (self->prerelease != mp_const_none) {
        snprintf(buf, sizeof(buf), "%u.%u.%u-%s",
                 self->major, self->minor, self->patch,
                 mp_obj_str_get_str(self->prerelease));
    } else {
        snprintf(buf, sizeof(buf), "%u.%u.%u",
                 self->major, self->minor, self->patch);
    }

    return mp_obj_new_str(buf, strlen(buf));
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_version_to_string_obj, refun_version_to_string);

// Version 类方法
static const mp_rom_map_elem_t refun_version_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_parse), MP_ROM_PTR(&refun_version_parse_obj) },
    { MP_ROM_QSTR(MP_QSTR_to_string), MP_ROM_PTR(&refun_version_to_string_obj) },
};
static MP_DEFINE_CONST_DICT(refun_version_locals_dict, refun_version_locals_dict_table);

// Version 类型定义
MP_DEFINE_CONST_OBJ_TYPE(
    refun_version_type,
    MP_QSTR_Version,
    MP_TYPE_FLAG_NONE,
    make_new, refun_version_make_new,
    print, refun_version_print,
    binary_op, refun_version_binary_op,
    locals_dict, &refun_version_locals_dict
);

//=============================================================================
// 约束对象实现
//=============================================================================

// 约束对象打印
static void refun_constraint_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    refun_constraint_obj_t *self = MP_OBJ_TO_PTR(self_in);

    const char *op_str = "";
    switch (self->op) {
        case CONSTRAINT_OP_EQ: op_str = "=="; break;
        case CONSTRAINT_OP_GTE: op_str = ">="; break;
        case CONSTRAINT_OP_GT: op_str = ">"; break;
        case CONSTRAINT_OP_LTE: op_str = "<="; break;
        case CONSTRAINT_OP_LT: op_str = "<"; break;
        case CONSTRAINT_OP_CARET: op_str = "^"; break;
        case CONSTRAINT_OP_TILDE: op_str = "~"; break;
    }

    mp_printf(print, "Constraint(%s %u.%u.%u)", op_str,
              self->version->major, self->version->minor, self->version->patch);
}

// Constraint.parse("^1.2.0")
mp_obj_t refun_constraint_parse(mp_obj_t str_obj) {
    const char *str = mp_obj_str_get_str(str_obj);

    constraint_op_t op;
    const char *version_str;

    // 解析操作符
    if (strncmp(str, "==", 2) == 0) {
        op = CONSTRAINT_OP_EQ;
        version_str = str + 2;
    } else if (strncmp(str, ">=", 2) == 0) {
        op = CONSTRAINT_OP_GTE;
        version_str = str + 2;
    } else if (strncmp(str, "<=", 2) == 0) {
        op = CONSTRAINT_OP_LTE;
        version_str = str + 2;
    } else if (*str == '>') {
        op = CONSTRAINT_OP_GT;
        version_str = str + 1;
    } else if (*str == '<') {
        op = CONSTRAINT_OP_LT;
        version_str = str + 1;
    } else if (*str == '^') {
        op = CONSTRAINT_OP_CARET;
        version_str = str + 1;
    } else if (*str == '~') {
        op = CONSTRAINT_OP_TILDE;
        version_str = str + 1;
    } else {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid constraint operator"));
    }

    // 跳过空格
    while (*version_str == ' ') version_str++;

    // 解析版本
    mp_obj_t version_obj = refun_version_parse(mp_obj_new_str(version_str, strlen(version_str)));

    // 创建约束对象
    refun_constraint_obj_t *constraint = m_new_obj(refun_constraint_obj_t);
    constraint->base.type = &refun_constraint_type;
    constraint->op = op;
    constraint->version = MP_OBJ_TO_PTR(version_obj);

    return MP_OBJ_FROM_PTR(constraint);
}
static MP_DEFINE_CONST_FUN_OBJ_1(refun_constraint_parse_obj, refun_constraint_parse);

// Constraint.matches(version) - 检查版本是否满足约束
bool refun_constraint_matches(refun_constraint_obj_t *constraint, refun_version_obj_t *version) {
    int cmp = refun_version_compare(version, constraint->version);

    switch (constraint->op) {
        case CONSTRAINT_OP_EQ:
            return cmp == 0;
        case CONSTRAINT_OP_GTE:
            return cmp >= 0;
        case CONSTRAINT_OP_GT:
            return cmp > 0;
        case CONSTRAINT_OP_LTE:
            return cmp <= 0;
        case CONSTRAINT_OP_LT:
            return cmp < 0;
        case CONSTRAINT_OP_CARET:
            // ^1.2.3 表示 >=1.2.3 且 <2.0.0
            if (cmp < 0) return false;
            if (constraint->version->major == 0) {
                // ^0.x.y 是特殊情况：只有 patch 可以增加
                return version->major == 0 && version->minor == constraint->version->minor;
            }
            return version->major == constraint->version->major;
        case CONSTRAINT_OP_TILDE:
            // ~1.2.3 表示 >=1.2.3 且 <1.3.0
            if (cmp < 0) return false;
            return version->major == constraint->version->major &&
                   version->minor == constraint->version->minor;
        default:
            return false;
    }
}

static mp_obj_t refun_constraint_matches_method(mp_obj_t self_in, mp_obj_t version_in) {
    if (!mp_obj_is_type(version_in, &refun_version_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("Expected Version object"));
    }

    refun_constraint_obj_t *self = MP_OBJ_TO_PTR(self_in);
    refun_version_obj_t *version = MP_OBJ_TO_PTR(version_in);

    return mp_obj_new_bool(refun_constraint_matches(self, version));
}
static MP_DEFINE_CONST_FUN_OBJ_2(refun_constraint_matches_obj, refun_constraint_matches_method);

// Constraint 类方法
static const mp_rom_map_elem_t refun_constraint_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_parse), MP_ROM_PTR(&refun_constraint_parse_obj) },
    { MP_ROM_QSTR(MP_QSTR_matches), MP_ROM_PTR(&refun_constraint_matches_obj) },
};
static MP_DEFINE_CONST_DICT(refun_constraint_locals_dict, refun_constraint_locals_dict_table);

// Constraint 类型定义
MP_DEFINE_CONST_OBJ_TYPE(
    refun_constraint_type,
    MP_QSTR_Constraint,
    MP_TYPE_FLAG_NONE,
    print, refun_constraint_print,
    locals_dict, &refun_constraint_locals_dict
);
