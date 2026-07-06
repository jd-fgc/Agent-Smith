Structure générale du server :
# Créer une instance FastMCP avec un nom

# Enregistrer chaque tool avec le décorateur @mcp.tool()
# → read_file, edit_file, list_files
# → search_code, search_function_or_class_definition_in_code, find_references
# → run_tests, get_patch, run_command

# Point d'entrée :
#   si lancé directement → stdio (défaut)
#   si lancé avec --http → streamable HTTP sur un port

Ce que chaque tool doit faire dans le server :


@mcp.tool()
def tool_read_file(filepath, start_line, end_line):
    # appeler la fonction de file_system_tools
    # convertir le résultat (liste) en string
    # retourner la string



run_tests(solution_code, test_list, test_imports):
    
    construire un script :
        # 1. les imports
        pour chaque import dans test_imports:
            ajouter "import ..."
        
        # 2. le code de la solution
        ajouter solution_code
        
        # 3. les tests avec gestion pass/fail
        pour chaque test dans test_list:
            essayer d'exécuter le test (assert ...)
            si ça passe → noter "PASS"
            si AssertionError → noter "FAIL: ..."
    
    retourner le script construit (str)



# task.json contient :
task_definition = "écrire une fonction qui additionne deux nombres"
function_definition = "def add(a, b):"
test_imports = []
test_list = [
    "assert add(2, 3) == 5",
    "assert add(0, 0) == 0",
    "assert add(-1, 1) == 0"
]

# Le LLM génère :
solution_code = "def add(a, b):\n    return a + b"

# run_tests() construit et retourne :
"""
def add(a, b):
    return a + b

try:
    assert add(2, 3) == 5
    print("PASS: assert add(2, 3) == 5")
except AssertionError:
    print("FAIL: assert add(2, 3) == 5")
...
"""