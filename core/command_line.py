#!/usr/bin/env python3
import gitlab
import os
import yaml
from jinja2 import Template, Undefined, Environment
from jinja2_base64_filters import jinja2_base64_filters

import xmlplain

class NullUndefined(Undefined):
  def __getattr__(self, key):
    return ''

class Gitlab:
    __instance = None
    @staticmethod
    def getInstance():
        """ Static access method. """
        if Gitlab.__instance == None:
            Gitlab()
        return Gitlab.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if Gitlab.__instance != None:
            return None
        else:
            gitlab_url = os.environ['PYTHON_GITLAB_URL']
            gitlab_token = os.environ['PYTHON_GITLAB_TOKEN']
            gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token, api_version=4)
            Gitlab.__instance = gl


########################################################################

def env(key):
  return os.getenv(key)

def t(text):
    t = Template(str(text), undefined=NullUndefined)
    t.globals['env'] = env
    return t.render()

def yml2xmlplain(value):
    root = xmlplain.obj_from_yaml(value)
    return xmlplain.xml_from_obj(root, pretty=True).decode("utf-8")

    #return xmlplain.xml_to_obj(value, strip_space=True, fold_dict=True)

def main():
    with open('variables.yml') as fd:
        data = yaml.safe_load(fd)

    for vType, tDataList in data.items():
        if vType == 'groups':
            apply_groups_vars(tDataList)
        if vType == 'projects':
            apply_projects_vars(tDataList)

def apply_groups_vars(tDataList):
    for tData in tDataList:
        group_id = t(tData['id'])
        apply_group_vars(group_id, tData['vars'])

def apply_projects_vars(tDataList):
    for tData in tDataList:
        project_id = t(tData['id'])
        apply_project_vars(project_id, tData['vars'])

def g_var_exists(gEntity, name):
    try:
        val = gEntity.variables.get(name)
        return True
    except gitlab.exceptions.GitlabGetError as e:
        if str(e)[0:3] == '404':
            return False
        else:
            print(e)

def g_var_apply(gEntity, name, value):
    if g_var_exists(gEntity, name):
        #print("Variable %s exists!" % name)
        var = gEntity.variables.get(name)
        var.value = value
        return var.save()
    else:
        #print("Variable %s not exists!" % name)
        return gEntity.variables.create({'key': name, 'value': value})

def g_g_apply_var(group_id, name, value):
    gl = Gitlab().getInstance()
    group = gl.groups.get(group_id)
    return g_var_apply(group, name, value)

def g_p_apply_var(project_id, name, value):
    gl = Gitlab().getInstance()
    project = gl.projects.get(project_id)
    return g_var_apply(project, name, value)

def t_var_value(var):
    value = t(var['value'])
    if 'jinja2_filters' in var:
        env = Environment(extensions=["jinja2_base64_filters.Base64Filters"])
        env.filters['yml2xmlplain'] = yml2xmlplain
        for filter in var['jinja2_filters']:
            value = env.from_string("{{fstr|" + filter + "}}").render(fstr=value)
    return value

def apply_group_vars(group_id, vars):
    for v in vars:
        g_g_apply_var(group_id, v['name'], t_var_value(v))

def apply_project_vars(project_id, vars):
    for v in vars:
        g_p_apply_var(project_id, v['name'], t_var_value(v))


if __name__ == "__main__":
    main()
