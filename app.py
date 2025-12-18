import re
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory ## CAMBIO: Importado send_from_directory
from sympy import symbols, Eq, nsolve, N, parse_expr, linear_eq_to_matrix, simplify, exp, log, sin, cos, tan, asin, acos, atan, sqrt, pi, E
from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application

## CAMBIO: Se indica que busque plantillas y archivos estáticos en la raíz '.'
app = Flask(__name__, template_folder='.', static_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

## CAMBIO: Nueva ruta para servir el archivo CSS desde la raíz
@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')

@app.route('/resolver', methods=['POST'])
def resolver():
    try:
        data = request.json
        v1_str, v2_str = data['var1'].strip(), data['var2'].strip()
        eq1_raw, eq2_raw = data['eq1'], data['eq2']
        
        # Validación de entrada de variables
        if not v1_str.isalpha() or not v2_str.isalpha() or v1_str == v2_str:
            return jsonify({'status': 'var_error', 'message': "Variables base no válidas."})

        def traducir(texto):
            texto = re.sub(r'e\^\((.*?)\)', r'exp(\1)', texto)
            texto = re.sub(r'log\((.*?),(.*?)\)', r'log(\2,\1)', texto)
            texto = texto.replace('π', 'pi').replace('√', 'sqrt').replace('ln', 'log')
            texto = re.sub(r'\be\b', 'E', texto)
            texto = texto.replace('^', '**')
            texto = texto.replace('sin^-1', 'asin').replace('cos^-1', 'acos').replace('tan^-1', 'atan')
            return texto

        v1, v2 = symbols(f'{v1_str} {v2_str}')
        t1, t2 = traducir(eq1_raw), traducir(eq2_raw)
        
        trans = (standard_transformations + (implicit_multiplication_application,))
        
        expr1 = parse_expr(t1, transformations=trans)
        expr2 = parse_expr(t2, transformations=trans)

        # --- JERARQUÍA 1: VALIDACIÓN DE VARIABLES ---
        simbolos_usados = expr1.free_symbols | expr2.free_symbols
        variables_permitidas = {v1, v2}
        solo_letras = {s for s in simbolos_usados if s.name not in ['pi', 'E', 'exp', 'log', 'I']}

        if not solo_letras.issubset(variables_permitidas):
            return jsonify({'status': 'var_error', 'message': "Variables no correspondientes"})

        # --- JERARQUÍA 2: IDENTIDADES (INFINITAS) ---
        if simplify(expr1 - expr2) == 0:
            return jsonify({'status': 'info', 'message': "El sistema tiene soluciones infinitas"})

        # Análisis de matriz para sistemas puramente lineales
        try:
            matrix, b = linear_eq_to_matrix([expr1, expr2], [v1, v2])
            rango_a = matrix.rank()
            rango_am = matrix.row_join(b).rank()
            if rango_a < 2:
                if rango_a == rango_am:
                    return jsonify({'status': 'info', 'message': "El sistema tiene soluciones infinitas"})
                else:
                    return jsonify({'status': 'info', 'message': "El sistema no tiene solución"})
        except:
            pass 

        # --- JERARQUÍA 3: BÚSQUEDA DE SOLUCIÓN ÚNICA ---
        soluciones_encontradas = []
        puntos_prueba = [-10, -1, 0, 1, 10]
        for px in puntos_prueba:
            for py in puntos_prueba:
                try:
                    sol_num = nsolve((expr1, expr2), (v1, v2), (px, py), prec=15, maxsteps=20)
                    vx, vy = round(float(N(sol_num[0])), 6), round(float(N(sol_num[1])), 6)
                    if (vx, vy) not in soluciones_encontradas:
                        soluciones_encontradas.append((vx, vy))
                except:
                    continue

        if len(soluciones_encontradas) > 1:
            return jsonify({'status': 'info', 'message': "sistema muy complejo que tiene dos o más soluciones"})
        
        if len(soluciones_encontradas) == 0:
            return jsonify({'status': 'info', 'message': "El sistema no tiene solución"})

        sol = soluciones_encontradas[0]
        final_res = [f"{v1_str} = {sol[0]}", f"{v2_str} = {sol[1]}"]
        return jsonify({'status': 'success', 'soluciones': [final_res]})

    except Exception as e:
        print(f"Error detectado: {e}")
        return jsonify({'status': 'error', 'message': "Error de sintaxis matemática."})

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000)) # La modificacion que se realizo aqui es por que render asigna un puerto automaticamente y tiene que detectarlo ya que lo tenias corriendo en tu compu
    app.run(host='0.0.0.0', port=port)