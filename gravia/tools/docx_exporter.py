import pypandoc
import os
import sys

def export_to_docx(tex_file_path, output_docx_path):
    """
    Converts LaTeX to beautifully styled DOCX using Pandoc.
    Maintains semantic integrity (Heading 1 remains Heading 1).
    """
    if not os.path.exists(tex_file_path):
        print(f"Error: {tex_file_path} not found.")
        return False

    try:
        print(f"Exporting manuscript to {output_docx_path} via Pandoc...")
        # extra_args for bibliographic processing if needed: ['--citeproc']
        # Converting the highly structured .tex into .docx using Pandoc's AST
        pypandoc.convert_file(
            tex_file_path, 'docx', 
            outputfile=output_docx_path, 
            extra_args=['--citeproc']
        )
        print(f"Successfully exported styled manuscript to {output_docx_path}")
        return True
    except OSError as e:
        # Check if Pandoc is installed as per directive
        if "pandoc" in str(e).lower():
            print("[ERROR] Pandoc not found. Please install it to use this feature.")
            # We'll assume the CLI or user_decision_router can catch this.
        else:
            print(f"Pandoc DOCX conversion OS error: {e}")
        return False
    except Exception as e:
        print(f"Pandoc DOCX conversion failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 2:
        export_to_docx(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python docx_exporter.py <tex_file_path> <output_docx_path>")
