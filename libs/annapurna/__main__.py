import sys

from .retriever import Retriever

def main():
    # Check if there are enough arguments.
    if len(sys.argv) < 3:
        print("At least two arguments (retriever ID & query) are required")
        sys.exit(1)

    retriever_id = sys.argv[1]
    retriever = Retriever(retriever_id)
    
    query = ' '.join(sys.argv[2:])
    retrieved = retriever.retrieve(query)
    print(retrieved)
    

if __name__ == "__main__":
    main()
