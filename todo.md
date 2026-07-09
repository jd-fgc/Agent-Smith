
student/
    agent/
        agent_mbpp.py        # CLI + boucle agent MBPP
        agent_swebench.py    # CLI + boucle agent SWE-bench
    sandbox/
        sandbox.py           # classe Sandbox + worker
    mcp/
        tools/
            file_system_tools.py
            code_search_tools.py
            execution_tools.py
            __init__.py
        mcp_tools_mbpp.py
        mcp_tools_swebench.py
    models/
        mbpp_models.py       # MBPPTaskInput, SolutionOutput, StepMetrics
        swe_models.py        # SWEBenchTaskInput
        sandbox_config.py    # SandboxConfig
    __main__.py              # point d'entrée sandbox REPL
    pyproject.toml

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


MBPP :
1. agent reçoit la tâche (function à écrire + tests)
2. LLM génère le code de la fonction
3. agent appelle run_tests() → construit un script Python
4. sandbox.execute(script) → exécute le script dans un process isolé
5. le script fait juste des assert et print PASS/FAIL
6. sandbox retourne le résultat à l'agent
7. agent renvoie le résultat au LLM pour itérer
Pas de tools MCP pendant l'exécution — juste du Python pur.

SWE-bench :
1. agent reçoit la tâche (bug dans un vrai repo)
2. LLM génère du code qui APPELLE des tools :
   result = read_file("/testbed/sympy/core.py", 1, 50)
   result = search_code("def solve", "*.py")
3. sandbox.execute(code) → exécute ce code
4. pendant l'exécution, le code appelle read_file()
   → le worker doit communiquer avec le process principal
   → qui appelle le MCP server
   → qui retourne le résultat
5. LLM itère jusqu'à trouver le bug et appeler final_answer()
