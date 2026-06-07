import ast, sys
files = [
    'src/frontend/app/pages/landing.py',
    'src/frontend/streamlit_app.py',
    'src/frontend/app/state.py',
]
ok = True
for f in files:
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print(f'OK: {f}')
    except SyntaxError as e:
        print(f'ERROR: {f} — {e}')
        ok = False
sys.exit(0 if ok else 1)
