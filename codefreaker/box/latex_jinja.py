"""This module provides a template-rendering function for Jinja2
that overrides Jinja2 defaults to make it work more seamlessly
with Latex.
"""

import re
from typing import Dict

import jinja2

######################################################################
# J2_ARGS
#   Constant was borrowed from Marc Brinkmann's
#   latex repository (mbr/latex on github)
######################################################################
J2_ARGS = {
    'block_start_string': r'\BLOCK{',
    'block_end_string': '}',
    'variable_start_string': r'\VAR{',
    'variable_end_string': '}',
    'comment_start_string': r'\#{',
    'comment_end_string': '}',
    'line_statement_prefix': '%-',
    'line_comment_prefix': '%#',
    'trim_blocks': True,
    'autoescape': False,
}

######################################################################
# Latex escape regex constants
######################################################################

# Organize all latex escape characters in one list
# (EXCEPT FOR ( "\" ), which is handled separately)
# escaping those which are special characters in
# PERL regular expressions
ESCAPE_CHARS = [
    r'\&',
    '%',
    r'\$',
    '#',
    '_',
    r'\{',
    r'\}',
    '~',
    r'\^',
]

# For each latex escape character, create a regular expression
# that matches all of the following criteria
# 1) one or two characters
# 2) if two characters, the first character is NOT a backslash ( "\" )
# 3) if two characters, the second, if one, the first character
#       is one of the latex escape characters
REGEX_ESCAPE_CHARS = [
    (re.compile(r'(?<!\\)' + i), r'\\' + i.replace('\\', '')) for i in ESCAPE_CHARS
]

# Place escape characters in [] for "match any character" regex
ESCAPE_CHARS_OR = r'[{}\\]'.format(''.join(ESCAPE_CHARS))

# For the back slash, create a regular expression
# that matches all of the following criteria
# 1) one, two, or three characters
# 2) the first character is not a backslash
# 3) the second character is a backslash
# 4) the third character is none of the ESCAPE_CHARS,
#       and is also not a backslash
REGEX_BACKSLASH = re.compile(r'(?<!\\)\\(?!{})'.format(ESCAPE_CHARS_OR))


######################################################################
# Declare module functions
######################################################################
def escape_latex_str_if_str(value):
    """Escape a latex string"""
    if not isinstance(value, str):
        return value
    for regex, replace_text in REGEX_ESCAPE_CHARS:
        value = re.sub(regex, replace_text, value)
    value = re.sub(REGEX_BACKSLASH, r'\\textbackslash{}', value)
    return value


######################################################################
# Declare module functions
######################################################################
def render_latex_template(path_templates, template_filename, template_vars=None) -> str:
    """Render a latex template, filling in its template variables

    :param path_templates: the path to the template directory
    :param template_filename: the name, rooted at the path_template_directory,
        of the desired template for rendering
    :param template_vars: dictionary of key:val for jinja2 variables
        defaults to None for case when no values need to be passed
    """
    var_dict = template_vars if template_vars else {}
    j2_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(path_templates), **J2_ARGS
    )
    j2_env.filters['escape'] = escape_latex_str_if_str
    template = j2_env.get_template(template_filename)
    return template.render(**var_dict)  # type: ignore


def render_latex_template_blocks(
    path_templates, template_filename, template_vars=None
) -> Dict[str, str]:
    """Render a latex template, filling in its template variables

    :param path_templates: the path to the template directory
    :param template_filename: the name, rooted at the path_template_directory,
        of the desired template for rendering
    :param template_vars: dictionary of key:val for jinja2 variables
        defaults to None for case when no values need to be passed
    """
    var_dict = template_vars if template_vars else {}
    j2_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(path_templates), **J2_ARGS
    )
    j2_env.filters['escape'] = escape_latex_str_if_str
    template = j2_env.get_template(template_filename)
    ctx = template.new_context(var_dict)  # type: ignore
    return {key: ''.join(value(ctx)) for key, value in template.blocks.items()}
