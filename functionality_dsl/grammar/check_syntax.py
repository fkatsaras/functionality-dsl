import glob
import os
from textx import metamodel_from_file

base_path = os.path.join(os.path.dirname(__file__))


def validate_grammar(grammar_file):
    try:
        file_name = os.path.basename(grammar_file)
        metamodel = metamodel_from_file(grammar_file)
        print(f"✅ The grammar '{file_name}' is valid!")
    except Exception as e:
        print(f"❌ Error in grammar '{file_name}': {e}")


if __name__ == "__main__":
    grammar_files = glob.glob(os.path.join(base_path, "*.tx"))
    if not grammar_files:
        print("⚠️ No grammar files found!")
    else:
        for file in grammar_files:
            validate_grammar(file)