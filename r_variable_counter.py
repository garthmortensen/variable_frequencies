import os
import re


def get_r_patterns():
    """Define and return regex patterns for R variable detection"""

    # Basic building blocks as named constants
    R_IDENTIFIER = r"""
        (?P<varname>         # Named capture group for the variable
            [a-zA-Z]         # Start with letter
            [a-zA-Z0-9_\.]*  # Followed by letters, numbers, underscores, or dots
        )
    """

    WHITESPACE = r"\s*"  # Optional whitespace

    # R-style assignment: var <- value
    # Example matches: x <- 10, my.var <- function(), data_frame <- read.csv()
    R_ASSIGN = rf"""
        {R_IDENTIFIER}       # Variable name
        {WHITESPACE}         # Optional whitespace
        <-                   # Left arrow assignment operator
    """

    # Walrus operator assignment: var := value
    # Example matches: x := 10, my.var := function()
    WALRUS_ASSIGN = rf"""
        {R_IDENTIFIER}       # Variable name
        {WHITESPACE}         # Optional whitespace
        :=                   # Walrus operator
    """

    # Standard equals assignment: var = value
    # Example matches: x = 10, my.var = function(), data_frame = read.csv()
    EQUALS_ASSIGN = rf"""
        {R_IDENTIFIER}       # Variable name
        {WHITESPACE}         # Optional whitespace
        =                    # Equals sign
    """

    # Pattern to find mutate() function calls with content inside
    # Example matches: mutate(x = 1), mutate(newvar = oldvar + 1, another = x * 2)
    MUTATE_PATTERN = r"""
        mutate               # mutate function name
        \s*                  # Optional whitespace
        \(                   # Opening parenthesis
        (?P<content>.*?)     # Content inside parentheses (non-greedy)
        \)                   # Closing parenthesis
    """

    patterns = {
        "r_assign": re.compile(R_ASSIGN, re.VERBOSE),
        "walrus": re.compile(WALRUS_ASSIGN, re.VERBOSE),
        "equals": re.compile(EQUALS_ASSIGN, re.VERBOSE),
        "mutate": re.compile(MUTATE_PATTERN, re.VERBOSE | re.DOTALL),
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
        "renv",  # R environment directory
    }
    return dirname in skip_dirs


def analyze_r_file(file_path, patterns):
    """Analyze a single R file and return variable counts"""

    local_counts = {}

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

            # Process R-style assignments (var <- value)
            for match in patterns["r_assign"].finditer(content):
                var = match.group("varname")
                local_counts[var] = local_counts.get(var, 0) + 1

            # Process walrus operator assignments (var := value)
            for match in patterns["walrus"].finditer(content):
                var = match.group("varname")
                local_counts[var] = local_counts.get(var, 0) + 1

            # Process mutate function blocks
            for mutate_block in patterns["mutate"].finditer(content):
                mutate_content = mutate_block.group("content")

                # Find all variable assignments inside mutate()
                for var_match in patterns["equals"].finditer(mutate_content):
                    var = var_match.group("varname")
                    local_counts[var] = local_counts.get(var, 0) + 1

            return local_counts, True

    except Exception as e:
        print(f"Error with {file_path}: {e}")
        return {}, False


def count_variables(directory):
    """Count variables in R files within a directory"""

    counts = {}
    processed_files = []
    patterns = get_r_patterns()

    # Using topdown=True allows us to modify dirs in-place to skip directories
    for root, dirs, files in os.walk(directory, topdown=True):
        # Modify dirs in-place to skip unwanted directories
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]

        for file in files:
            if file.endswith(".R") or file.endswith(".r"):
                path = os.path.join(root, file)
                file_counts, success = analyze_r_file(path, patterns)

                # Update global counts
                for var, count in file_counts.items():
                    counts[var] = counts.get(var, 0) + count

                if success:
                    processed_files.append(path)

    # Sort variables by frequency (most frequent first)
    sorted_vars = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_vars, processed_files


def save_results(results, processed_files, prefix="r"):
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


def print_summary(results, processed_files, prefix="R"):
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
        print("Usage: python r_variable_analyzer.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    results, processed_files = count_variables(directory)
    filenames = save_results(results, processed_files)
    print(f"Results saved to {filenames[0]} and {filenames[1]}")
    print_summary(results, processed_files)
