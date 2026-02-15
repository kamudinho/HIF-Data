streamlit.errors.StreamlitDuplicateElementId: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:
File "/mount/src/hif-data/HIF-dash.py", line 150, in <module>
    import tools.scout_db as sdb
File "/mount/src/hif-data/tools/scout_db.py", line 119, in <module>
    hoved_omraade = option_menu(
        menu_title=None,
    ...<6 lines>...
        }
    )
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit_option_menu/__init__.py", line 66, in option_menu
    component_value = _component_func(options=options,
                key=key, defaultIndex=default_index, icons=icons, menuTitle=menu_title,
                menuIcon=menu_icon, default=options[default_index],
                orientation=orientation, styles=styles, manualSelect=manual_select, on_change=_on_change)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/components/v1/custom_component.py", line 57, in __call__
    return self.create_instance(
           ~~~~~~~~~~~~~~~~~~~~^
        *args,
        ^^^^^^
    ...<4 lines>...
        **kwargs,
        ^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/metrics_util.py", line 532, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/components/v1/custom_component.py", line 214, in create_instance
    return_value = marshall_component(dg, element)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/components/v1/custom_component.py", line 174, in marshall_component
    computed_id = compute_and_register_element_id(
        "component_instance",
    ...<9 lines>...
        special_args=special_args,
    )
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/lib/utils.py", line 265, in compute_and_register_element_id
    _register_element_id(ctx, element_type, element_id)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/elements/lib/utils.py", line 150, in _register_element_id
    raise StreamlitDuplicateElementId(element_type)
