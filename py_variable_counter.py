import os
import re


def get_python_patterns():
    """Define and return regex patterns for Python variable detection"""

    # Basic building blocks as named constants
    # Named capture version for direct use
    IDENTIFIER_NAMED = r"""
        (?P<varname>         # Named capture group for the variable
            [a-zA-Z_]        # Start with letter or underscore
            [a-zA-Z0-9_]*    # Followed by letters, numbers, or underscores
        )
    """

    # Non-capturing version for use in repeated contexts
    IDENTIFIER_RAW = r"""
        [a-zA-Z_]            # Start with letter or underscore
        [a-zA-Z0-9_]*        # Followed by letters, numbers, or underscores
    """

    WHITESPACE = r"\s*"  # Optional whitespace

    # Standard equals assignment: var = value
    EQUALS_ASSIGN = rf"""
        {IDENTIFIER_NAMED}   # Variable name
        {WHITESPACE}         # Optional whitespace
        =                    # Equals sign
        (?!=)                # Negative lookahead to avoid matching == comparison
    """

    # Walrus operator assignment: var := value (Python 3.8+)
    WALRUS_ASSIGN = rf"""
        {IDENTIFIER_NAMED}   # Variable name
        {WHITESPACE}         # Optional whitespace
        :=                   # Walrus operator
    """

    # Multiple assignment pattern: var1, var2 = value1, value2
    # Using the non-captured version to avoid name conflicts
    MULTI_ASSIGN = rf"""
        (                    # Group for the list of variables
            {IDENTIFIER_RAW} # First variable (non-capturing)
            (?:              # Non-capturing group for additional variables
                {WHITESPACE},  # Comma separator
                {WHITESPACE}   # Optional whitespace
                {IDENTIFIER_RAW}  # Additional variable (non-capturing)
            )+               # One or more additional variables
        )
        {WHITESPACE}         # Optional whitespace
        =                    # Equals sign
    """

    # Augmented assignments (+=, -=, *=, /=, etc.)
    AUGMENTED_ASSIGN = rf"""
        {IDENTIFIER_NAMED}   # Variable name
        {WHITESPACE}         # Optional whitespace
        (?P<operator>        # Named capture for the operator
            [+\-*/%@&|^]=    # Single-character augmented assignments
            |                # OR
            //=              # Floor division
            |                # OR
            >>=              # Right shift
            |                # OR
            <<=              # Left shift
            |                # OR
            \*\*=            # Exponentiation
        )
    """

    # For loop variable pattern
    FOR_LOOP = rf"""
        for                  # For keyword
        {WHITESPACE}         # Whitespace
        {IDENTIFIER_NAMED}   # Loop variable
        {WHITESPACE}         # Whitespace
        in                   # in keyword
    """

    # Simple pattern to extract variable names from multi-assigns
    VAR_EXTRACTOR = r"""
        (?P<varname>         # Named capture for variable name
            [a-zA-Z_]        # Start with letter or underscore
            [a-zA-Z0-9_]*    # Followed by letters, numbers, or underscores
        )
    """

    patterns = {
        "equals": re.compile(EQUALS_ASSIGN, re.VERBOSE),
        "walrus": re.compile(WALRUS_ASSIGN, re.VERBOSE),
        "multi_assign": re.compile(MULTI_ASSIGN, re.VERBOSE),
        "augmented": re.compile(AUGMENTED_ASSIGN, re.VERBOSE),
        "for_loop": re.compile(FOR_LOOP, re.VERBOSE),
        "var_name": re.compile(
            VAR_EXTRACTOR, re.VERBOSE
        ),  # Used for extracting from multi-assigns
    }

    return patterns


def should_skip_directory(dirname):
    """Check if a directory should be skipped during analysis"""
    # List of directories to skip
    skip_dirs = {
        ".git",  # Git repository
        "venv",  # Virtual environment
        ".venv",  # Alternative virtual environment name
        "env",  # Another common virtual environment name
        "__pycache__",  # Python cache directories
        "node_modules",  # Node.js modules
        ".pytest_cache",  # pytest cache
        ".mypy_cache",  # mypy cache
        ".tox",  # tox testing directories
        "dist",  # Distribution directories
        "build",  # Build directories
        ".idea",  # JetBrains IDE files
        ".vscode",  # VS Code files
        ".ipynb_checkpoints",  # Jupyter notebook checkpoints
    }
    return dirname in skip_dirs


def analyze_python_file(file_path, patterns):
    """Analyze a single Python file and return variable counts"""

    local_counts = {}

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

            # Process standard assignments (var = value)
            for match in patterns["equals"].finditer(content):
                var = match.group("varname")
                # Skip keywords that might be followed by comparison
                if var not in (
                    "if",
                    "while",
                    "for",
                    "elif",
                    "return",
                    "and",
                    "or",
                    "not",
                    "is",
                    "in",
                    "None",
                    "True",
                    "False",
                ):
                    local_counts[var] = local_counts.get(var, 0) + 1

            # Process walrus operator assignments (var := value)
            for match in patterns["walrus"].finditer(content):
                var = match.group("varname")
                local_counts[var] = local_counts.get(var, 0) + 1

            # Process multiple assignments (x, y = 1, 2)
            for match in patterns["multi_assign"].finditer(content):
                var_list = match.group(1)
                for var_match in patterns["var_name"].finditer(var_list):
                    var_name = var_match.group("varname")
                    local_counts[var_name] = local_counts.get(var_name, 0) + 1

            # Process augmented assignments (x += 1, etc.)
            for match in patterns["augmented"].finditer(content):
                var = match.group("varname")
                local_counts[var] = local_counts.get(var, 0) + 1

            # Process for loop variables
            for match in patterns["for_loop"].finditer(content):
                var = match.group("varname")
                local_counts[var] = local_counts.get(var, 0) + 1

            return local_counts, True

    except Exception as e:
        print(f"Error with {file_path}: {e}")
        return {}, False


def count_variables(directory):
    """Count variables in Python files within a directory"""

    counts = {}
    processed_files = []
    patterns = get_python_patterns()

    # Using topdown=True allows us to modify dirs in-place to skip directories
    for root, dirs, files in os.walk(directory, topdown=True):
        # Modify dirs in-place to skip unwanted directories
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]

        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                file_counts, success = analyze_python_file(path, patterns)

                # Update global counts
                for var, count in file_counts.items():
                    counts[var] = counts.get(var, 0) + count

                if success:
                    processed_files.append(path)

    # Sort variables by frequency (most frequent first)
    sorted_vars = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_vars, processed_files


def save_results(results, processed_files, prefix="python"):
    """Save variable counts and processed files to output files"""

    filename_vars = f"{prefix}_var_counts.csv"
    with open(filename_vars, "w") as f:
        f.write("var,count\n")
        for var, count in results:
            f.write(f"{var},{count}\n")

    filename_files = f"processed_{prefix}_files.txt"
    with open(filename_files, "w") as f:
        for file_path in processed_files:
            f.write(f"{file_path}\n")

    return filename_vars, filename_files


def print_summary(results, processed_files, prefix="Python"):
    """Print summary of analysis results"""

    print(f"Found {len(results)} {prefix} variables")
    print(f"Processed {len(processed_files)} {prefix} scripts")

    # top variables
    num_top_vars = min(10, len(results))  # Show top 10 or all if less than 10
    if results:
        print(f"\n{prefix} variables (descending freq):")
        print(f"{'\tVARIABLE':<30} {'N':<10}")
        for var, count in results[:num_top_vars]:
            print(f"\t{var:<30}{count:<10}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python python_variable_analyzer.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    results, processed_files = count_variables(directory)
    filenames = save_results(results, processed_files)
    print(f"Results saved to {filenames[0]} and {filenames[1]}")
    print_summary(results, processed_files)
