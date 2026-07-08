

**Resumer  method**

execution_tools.py
run_tests(solution_code, test_list, test_imports) → str
    construit un script Python prêt à être exécuté

get_patch() → dict {stdout, stderr, output}
    fait un git diff

run_command(command, workdir) → dict {stdout, stderr, output}
    exécute une commande shell

file_system_tools.py
read_file(filepath, start_line, end_line) → List[str]
edit_file(filepath, old_str, new_str) → None
list_files(directory, pattern) → List[str]

code_search_tools.py
search_code(pattern, file_pattern) → List[str]
search_function_or_class_definition_in_code(name) → List[str]
find_references(name, filepath, line) → List[str]

mcp_tools_mbpp.py
FastMCP server "agent-smith"
expose : tool_run_tests
lancé en stdio par défaut, HTTP avec --http

mcp_tools_swebench.py
FastMCP server "agent-smith"
expose : tool_read_file, tool_edit_file, tool_list_file,
         tool_search_code, tool_search_function_or_class_definition_in_code,
         tool_find_references, tool_get_patch, tool_run_command
lancé en stdio par défaut, HTTP avec --http

