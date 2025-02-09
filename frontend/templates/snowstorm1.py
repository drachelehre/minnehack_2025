class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def build_tree(rpn_expr):
    stack = []

    for token in rpn_expr:
        node = Node(token)
        if token in "+-*/":
            if len(stack) < 2:
                raise ValueError("Invalid RPN expression: the stack should have at least two elements for an operator")
            
            node.right = stack.pop()
            node.left = stack.pop()
        
        stack.append(node)
    # After processing all tokens, there should be exactly one element in the stack
    if len(stack) != 1:
        raise ValueError("Invalid RPN expression: the stack should have exactly one element at the end")
    
    return stack[0]

def print_tree(root, level=0, side=" "):
    if root:
        print(" " * (level * 4) + side + root.value)
        if root.left or root.right:
            print_tree(root.left, level + 1, "/\\")
            print_tree(root.right, level + 1, "/  ")

def rpn_parser(expression):
    # Tokenize the RPN expression
    tokens = expression.split()
    
    try:
        # Build the tree from RPN
        root = build_tree(tokens)
        
        # Print the tree
        print_tree(root)
    
    except ValueError as e:
        print(f"Error: {e}")

# Examples
print("For (+ 3 4):")
rpn_parser("+ 3 4")

print("\nFor (* (+ 3 4) 2):")
rpn_parser("* + 3 4 2")

# Example of an invalid expression
print("\nFor an invalid expression:")
rpn_parser("+ 3")