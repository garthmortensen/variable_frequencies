import os
import sys
import re
from py_variable_counter import count_variables as count_python_vars
from py_variable_counter import print_summary as print_python_summary
from py_variable_counter import save_results as save_python_results
from r_variable_counter import count_variables as count_r_vars
from r_variable_counter import print_summary as print_r_summary
from r_variable_counter import save_results as save_r_results

def generate_combined_report(py_results, r_results, output_file="combined_vars.csv"):
    """Generate a combined report of Python and R variables"""
    
    # Combine results and mark language
    combined = []
    for var, count in py_results:
        combined.append((var, count, "python"))
    for var, count in r_results:
        combined.append((var, count, "r"))
    
    # Sort by count (descending)
    combined.sort(key=lambda x: x[1], reverse=True)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write("var,count,language\n")
        for var, count, lang in combined:
            f.write(f"{var},{count},{lang}\n")
    
    return output_file

def find_shared_variables(py_results, r_results):
    """Find variables used in both Python and R code"""
    
    py_vars = {var for var, _ in py_results}
    r_vars = {var for var, _ in r_results}
    shared = py_vars.intersection(r_vars)
    
    # Get counts for shared variables
    shared_with_counts = []
    py_dict = dict(py_results)
    r_dict = dict(r_results)
    
    for var in shared:
        shared_with_counts.append((var, py_dict[var], r_dict[var]))
    
    # Sort by total count
    shared_with_counts.sort(key=lambda x: x[1] + x[2], reverse=True)
    
    return shared_with_counts

def print_combined_summary(py_results, py_files, r_results, r_files, shared_vars):
    """Print a combined summary of analysis results"""
    
    print("\n===== COMBINED SUMMARY =====")
    print(f"Total files processed: {len(py_files) + len(r_files)}")
    print(f"Total variables found: {len(py_results) + len(r_results)}")
    print(f"Shared variables: {len(shared_vars)}")
    
    if shared_vars:
        print("\nTop shared variables (Python count, R count):")
        print(f"{'\tVARIABLE':<30} {'PYTHON':<10} {'R':<10}")
        for var, py_count, r_count in shared_vars[:10]:
            print(f"\t{var:<30}{py_count:<10}{r_count:<10}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python code_analyzer.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    # Run Python analysis
    print("===== ANALYZING PYTHON FILES =====")
    py_results, py_files = count_python_vars(directory)
    py_filenames = save_python_results(py_results, py_files)
    print(f"Results saved to {py_filenames[0]} and {py_filenames[1]}")
    print_python_summary(py_results, py_files)
    
    # Run R analysis
    print("\n===== ANALYZING R FILES =====")
    r_results, r_files = count_r_vars(directory)
    r_filenames = save_r_results(r_results, r_files)
    print(f"Results saved to {r_filenames[0]} and {r_filenames[1]}")
    print_r_summary(r_results, r_files)
    
    # Generate combined report
    combined_file = generate_combined_report(py_results, r_results)
    print(f"\nCombined results saved to {combined_file}")
    
    # Find shared variables
    shared_vars = find_shared_variables(py_results, r_results)
    
    # Print combined summary
    print_combined_summary(py_results, py_files, r_results, r_files, shared_vars)
    
    # Intentional code duplication - save shared variables to file
    with open("shared_variables.csv", 'w') as f:
        f.write("var,python_count,r_count,total\n")
        for var, py_count, r_count in shared_vars:
            f.write(f"{var},{py_count},{r_count},{py_count+r_count}\n")
    
    print(f"Shared variables saved to shared_variables.csv")
