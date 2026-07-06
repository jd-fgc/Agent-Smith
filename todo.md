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