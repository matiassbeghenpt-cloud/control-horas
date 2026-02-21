from flask import Flask, request, redirect, send_file
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json
import os

app = Flask(__name__)

ARCHIVO = "datos.json"

# ---------- CARGAR DATOS ----------
if os.path.exists(ARCHIVO):
    with open(ARCHIVO,"r") as f:
        registros = json.load(f)
else:
    registros = []

# ---------- GUARDAR DATOS ----------
def guardar():
    with open(ARCHIVO,"w") as f:
        json.dump(registros,f)

# ---------- TARIFA ----------
def calcular_precio(fecha_texto, fuera_portugal):
    fecha = datetime.strptime(fecha_texto,"%Y-%m-%d")
    es_fin_semana = fecha.weekday() >= 5

    if fuera_portugal=="si":
        return 14 if es_fin_semana else 12
    else:
        return 12 if es_fin_semana else 10

# ---------- HOME ----------
@app.route("/")
def inicio():

    html="<h1>Control de Horas</h1>"
    html+="<a href='/agregar'>Añadir horas</a><br>"
    html+="<a href='/pdf'>Generar PDF</a><br><br>"

    total_horas=0
    total_dinero=0

    for r in registros:
        horas=float(r["horas"])
        precio=calcular_precio(r["fecha"],r["fuera"])
        dinero=horas*precio

        total_horas+=horas
        total_dinero+=dinero

        lugar="Fuera PT" if r["fuera"]=="si" else "Portugal"

        html+=f"<p>{r['fecha']} | {r['cliente']} | {lugar} | {horas}h | {precio}€/h | {dinero:.2f}€</p>"

    html+="<hr>"
    html+=f"<h3>Total horas: {total_horas}</h3>"
    html+=f"<h3>Total dinero: {total_dinero:.2f} €</h3>"

    return html

# ---------- AGREGAR ----------
@app.route("/agregar",methods=["GET","POST"])
def agregar():

    if request.method=="POST":

        registros.append({
            "fecha":request.form["fecha"],
            "cliente":request.form["cliente"],
            "horas":request.form["horas"],
            "fuera":request.form["fuera"]
        })

        guardar()
        return redirect("/")

    return """
    <h1>Añadir Horas</h1>
    <form method="POST">

        Fecha:<br>
        <input type="date" name="fecha" required><br><br>

        Cliente:<br>
        <input type="text" name="cliente" required><br><br>

        Horas:<br>
        <input type="number" name="horas" step="0.1" required><br><br>

        ¿Fuera de Portugal?<br>
        <select name="fuera">
            <option value="no">No</option>
            <option value="si">Sí</option>
        </select><br><br>

        <button type="submit">Guardar</button>

    </form>
    """

# ---------- PDF ----------
@app.route("/pdf")
def generar_pdf():

    archivo="reporte_horas.pdf"
    doc=SimpleDocTemplate(archivo)
    estilos=getSampleStyleSheet()
    elementos=[]

    elementos.append(Paragraph("Reporte de Horas",estilos["Heading1"]))
    elementos.append(Spacer(1,12))

    tabla=[["Fecha","Cliente","Lugar","Horas","€/h","Total €"]]

    total_horas=0
    total_dinero=0

    for r in registros:
        horas=float(r["horas"])
        precio=calcular_precio(r["fecha"],r["fuera"])
        dinero=horas*precio

        lugar="Fuera PT" if r["fuera"]=="si" else "Portugal"

        tabla.append([
            r["fecha"],
            r["cliente"],
            lugar,
            str(horas),
            str(precio),
            f"{dinero:.2f}"
        ])

        total_horas+=horas
        total_dinero+=dinero

    tabla.append(["","","TOTAL",str(total_horas),"",f"{total_dinero:.2f}"])

    elementos.append(Table(tabla))
    doc.build(elementos)

    return send_file(archivo,as_attachment=True)

# ---------- RUN ----------
if __name__=="__main__":
    app.run(debug=True)