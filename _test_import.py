import ast, os, sys, traceback

# Check syntax of all AI files
files = [
    'src/backend/app/ai/mo_hinh_ai.py',
    'src/backend/app/ai/gcn_flow.py',
    'src/backend/app/ai/fuzzy_layer.py',
    'src/backend/app/ai/huan_luyen.py',
    'src/backend/app/ai/gnn_algorithm.py',
    'src/backend/app/ai/inference_service.py',
]
for f in files:
    if os.path.exists(f):
        try:
            ast.parse(open(f, encoding='utf-8').read())
            print('OK:', f)
        except SyntaxError as e:
            print('SYNTAX ERROR:', f, e)

# Try create_app
sys.path.insert(0, 'src/backend')
sys.path.insert(0, 'src')
try:
    from app import create_app
    result = create_app()
    print("create_app OK:", result)
except Exception as e:
    traceback.print_exc()
    print("create_app ERROR:", e)
