from flask import Flask, request, redirect, send_file, session
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
import json, os, io

app = Flask(__name__)
app.secret_key="clave"

ARCHIVO="datos.json"
ARCHIVO_USERS="usuarios.json"
ARCHIVO_CLIENTES="clientes.json"
ARCHIVO_FERIADOS="feriados.json"

BOOTSTRAP = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body{background:#f5f6fa;transition:0.3s}
.dark{background:#121212;color:white}
.dark .card{background:#1f1f1f;color:white}
.card{border-radius:16px}
.logo{height:45px}
</style>

<script>
function toggleDark(){
document.body.classList.toggle("dark")
localStorage.setItem("dark",document.body.classList.contains("dark"))
}
window.onload=function(){
if(localStorage.getItem("dark")==="true"){document.body.classList.add("dark")}
}
</script>
"""

# ---------- CARGAR ----------
def cargar(path,default):
    if os.path.exists(path):
        with open(path,"r") as f:
            return json.load(f)
    return default

registros=cargar(ARCHIVO,[])
usuarios=cargar(ARCHIVO_USERS,[{"user":"admin","pwd":"1234","funcion":"Admin"}])
clientes=cargar(ARCHIVO_CLIENTES,[])
feriados=set(cargar(ARCHIVO_FERIADOS,[]))

def guardar():
    json.dump(registros,open(ARCHIVO,"w"))
    json.dump(usuarios,open(ARCHIVO_USERS,"w"))
    json.dump(clientes,open(ARCHIVO_CLIENTES,"w"))

# ---------- UTIL ----------
def login_ok(): return "user" in session
def es_admin(): return session.get("user")=="admin"

def horas(i,f):
    if not i or not f: return 0
    try:
        t1=datetime.strptime(i,"%H:%M")
        t2=datetime.strptime(f,"%H:%M")
        return (t2-t1).seconds/3600
    except:
        return 0

def semana_rango(offset=0):
    hoy=datetime.today().date()
    lunes=hoy - timedelta(days=hoy.weekday()) + timedelta(days=offset*7)
    return lunes,lunes+timedelta(days=6)

def en_semana(fecha,offset):
    if not fecha: return False
    try:
        f=datetime.strptime(fecha,"%Y-%m-%d").date()
    except:
        return False
    ini,fin=semana_rango(offset)
    return ini<=f<=fin

# ---------- LOGIN ----------
@app.route("/login",methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        for u in usuarios:
            if u["user"]==request.form["user"] and u["pwd"]==request.form["pwd"]:
                session["user"]=u["user"]
                return redirect("/")
        msg="<div class='alert alert-danger'>Login incorrecto</div>"

    return f"""
<!doctype html>
<html>
<head>{BOOTSTRAP}<title>Login</title></head>
<body class="d-flex align-items-center" style="height:100vh">

<div class="container">
<div class="row justify-content-center">
<div class="col-md-4">
<div class="card shadow p-4">

<div class="text-center mb-3">
<img src="/static/logo.png" class="logo">
</div>

<h3 class="text-center mb-3">Login</h3>
{msg}

<form method="POST">
<input class="form-control mb-2" name="user" placeholder="Usuario">
<input class="form-control mb-3" type="password" name="pwd" placeholder="Password">
<button class="btn btn-primary w-100">Entrar</button>
</form>

</div>
</div>
</div>
</div>
</body>
</html>
"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- HOME ----------
@app.route("/")
def inicio():

    if not login_ok(): return redirect("/login")

    offset=int(request.args.get("semana",0))
    usuario=session["user"]
    ini,fin=semana_rango(offset)

    # -------- CALCULAR TOTALES SEMANA --------
    total_semana=0
    filas=""

    for i,r in enumerate(registros):
        if r.get("user")!=usuario: continue
        if not en_semana(r.get("fecha"),offset): continue

        h=horas(r.get("m1",""),r.get("m2",""))+horas(r.get("t1",""),r.get("t2",""))
        total_semana+=h

        filas+=f"""
        <tr>
        <td>{r.get('fecha','-')}</td>
        <td>{r.get('cliente','-')}</td>
        <td>{h}h</td>
        <td>
        <a class="btn btn-sm btn-outline-primary" href='/editar/{i}'>Editar</a>
        <a class="btn btn-sm btn-outline-danger" href='/borrar/{i}'>Borrar</a>
        </td>
        </tr>
        """

    boton_admin = "<a class='btn btn-warning btn-sm' href='/admin'>Admin</a>" if es_admin() else ""

    return f"""
<!doctype html>
<html>
<head>{BOOTSTRAP}<title>Horas</title></head>
<body>

<div class="container mt-4">
<div class="card shadow p-4">

<div class="d-flex justify-content-between align-items-center">
<div>
<img src="/static/logo.png" class="logo me-2">
<b>{usuario}</b>
</div>

<button onclick="toggleDark()" class="btn btn-sm btn-outline-secondary">🌙</button>
</div>

<p class="text-muted mt-2">{ini} → {fin}</p>

<h5 class="mb-3">Total semana: <b>{round(total_semana,2)} h</b></h5>

<div class="mb-3">
<a class="btn btn-outline-secondary btn-sm" href='/?semana={offset-1}'>⬅</a>
<a class="btn btn-outline-primary btn-sm" href='/?semana=0'>Hoy</a>
<a class="btn btn-outline-secondary btn-sm" href='/?semana={offset+1}'>➡</a>
</div>

<div class="mb-3">
<a class="btn btn-success btn-sm" href='/agregar'>Añadir jornada</a>
<a class="btn btn-danger btn-sm" href='/pdf?semana={offset}'>PDF</a>
<a class="btn btn-success btn-sm" href='/whatsapp?semana={offset}'>WhatsApp</a>
{boton_admin}
<a class="btn btn-dark btn-sm" href='/logout'>Salir</a>
</div>

<table class="table table-striped table-hover">
<thead><tr><th>Fecha</th><th>Cliente</th><th>Horas</th><th></th></tr></thead>
<tbody>{filas}</tbody>
</table>

</div>
</div>
</body>
</html>
"""

# ---------- ADMIN ----------
@app.route("/admin")
def admin():
    if not es_admin(): return redirect("/")

    lista_users="".join([
        f"<li class='list-group-item d-flex justify-content-between'>{u['user']} ({u.get('funcion','')}) <a class='btn btn-sm btn-danger' href='/del_user/{u['user']}'>Eliminar</a></li>"
        for u in usuarios if u["user"]!="admin"
    ])

    lista_clientes="".join([
        f"<li class='list-group-item d-flex justify-content-between'>{c} <a class='btn btn-sm btn-danger' href='/del_cliente/{c}'>Eliminar</a></li>"
        for c in clientes
    ])

    return f"""
<!doctype html>
<html>
<head>{BOOTSTRAP}<title>Admin</title></head>
<body>

<div class="container mt-4">
<div class="card shadow p-4">

<h3>Panel admin</h3>

<h5>Usuarios</h5>
<ul class="list-group mb-3">{lista_users}</ul>

<form method='POST' action='/add_user' class="mb-4">
<input class="form-control mb-2" name='user' placeholder="Usuario">
<input class="form-control mb-2" name='pwd' placeholder="Password">
<input class="form-control mb-2" name='funcion' placeholder="Función">
<button class="btn btn-primary">Crear usuario</button>
</form>

<h5>Clientes</h5>
<ul class="list-group mb-3">{lista_clientes}</ul>

<form method='POST' action='/add_cliente'>
<input class="form-control mb-2" name='cliente' placeholder="Nuevo cliente">
<button class="btn btn-success">Agregar cliente</button>
</form>

<a class="btn btn-secondary mt-3" href="/">Volver</a>

</div>
</div>
</body>
</html>
"""

@app.route("/add_user",methods=["POST"])
def add_user():
    if not es_admin(): return redirect("/")
    usuarios.append({"user":request.form["user"],"pwd":request.form["pwd"],"funcion":request.form.get("funcion","")})
    guardar()
    return redirect("/admin")

@app.route("/del_user/<u>")
def del_user(u):
    if not es_admin(): return redirect("/")
    global usuarios
    usuarios=[x for x in usuarios if x["user"]!=u]
    guardar()
    return redirect("/admin")

@app.route("/add_cliente",methods=["POST"])
def add_cliente():
    if not es_admin(): return redirect("/")
    c=request.form["cliente"]
    if c not in clientes: clientes.append(c)
    guardar()
    return redirect("/admin")

@app.route("/del_cliente/<c>")
def del_cliente(c):
    if not es_admin(): return redirect("/")
    global clientes
    clientes=[x for x in clientes if x!=c]
    guardar()
    return redirect("/admin")

# ---------- AGREGAR ----------
@app.route("/agregar",methods=["GET","POST"])
def agregar():

    if not login_ok(): return redirect("/login")

    if request.method=="POST":
        cliente=request.form["cliente"]
        if cliente not in clientes: clientes.append(cliente)

        registros.append({
            "fecha":request.form["fecha"],
            "cliente":cliente,
            "m1":request.form.get("m1",""),
            "m2":request.form.get("m2",""),
            "t1":request.form.get("t1",""),
            "t2":request.form.get("t2",""),
            "user":session["user"]
        })
        guardar()
        return redirect("/")

    opciones="".join([f"<option>{c}</option>" for c in clientes])

    return f"""
<!doctype html>
<html>
<head>{BOOTSTRAP}<title>Añadir</title></head>
<body>

<div class="container mt-4">
<div class="card shadow p-4">

<h3>Añadir jornada</h3>

<form method="POST">
<input type="date" class="form-control mb-2" name="fecha">
<input list="clientes" class="form-control mb-2" name="cliente">
<datalist id="clientes">{opciones}</datalist>

<input type="time" class="form-control mb-2" name="m1">
<input type="time" class="form-control mb-2" name="m2">
<input type="time" class="form-control mb-2" name="t1">
<input type="time" class="form-control mb-2" name="t2">

<button class="btn btn-success mt-2">Guardar</button>
<a class="btn btn-secondary mt-2" href="/">Volver</a>
</form>

</div>
</div>
</body>
</html>
"""

# ---------- BORRAR ----------
@app.route("/borrar/<int:i>")
def borrar(i):

    if not login_ok(): return redirect("/login")
    r=registros[i]

    if r.get("user")!=session["user"] and not es_admin():
        return redirect("/")

    registros.pop(i)
    guardar()
    return redirect("/")

# ---------- PDF ----------
@app.route("/pdf")
def pdf():

    if not login_ok(): return redirect("/login")

    offset=int(request.args.get("semana",0))
    usuario=session["user"]

    funcion=""
    for u in usuarios:
        if u["user"]==usuario:
            funcion=u.get("funcion","")
            break

    semana=[r for r in registros if r.get("user")==usuario and en_semana(r.get("fecha"),offset)]
    clientes_semana=list({r.get("cliente","") for r in semana if r.get("cliente")})

    packet=io.BytesIO()
    c=canvas.Canvas(packet,pagesize=A4)
    c.setFont("Helvetica",12)

    hoy=datetime.today().strftime("%d %m %Y")
    c.drawString(510,718,hoy)

    if len(clientes_semana)==1:
        c.drawString(150,717,clientes_semana[0])
    elif len(clientes_semana)>1:
        c.drawString(150,717," / ".join(clientes_semana))

    c.drawString(200,700,usuario)
    c.drawString(450,700,funcion)

    y=597
    total_n=total_a=total_b=total_c=0

    for r in semana:

        fecha_original=r.get("fecha","")

        try: dia=datetime.strptime(fecha_original,"%Y-%m-%d").weekday()
        except: dia=0

        try: fecha=datetime.strptime(fecha_original,"%Y-%m-%d").strftime("%d %m %Y")
        except: fecha=fecha_original

        total=horas(r.get("m1",""),r.get("m2",""))+horas(r.get("t1",""),r.get("t2",""))

        n=a=b=c_h=0
        if dia<5:
            n=min(8,total); a=max(0,total-8)
        elif dia==5: b=total
        else: c_h=total

        total_n+=n; total_a+=a; total_b+=b; total_c+=c_h

        c.drawString(75,y,fecha)
        if n>0: c.drawString(303,y,str(n))
        if a>0: c.drawString(323,y,str(a))
        if b>0: c.drawString(345,y,str(b))
        if c_h>0: c.drawString(370.5,y,str(c_h))

        cliente=r.get("cliente","")
        if len(clientes_semana)>1 and cliente:
            c.drawString(470,y,cliente)

        y-=17

    c.drawString(303,375,str(total_n))
    c.drawString(323,375,str(total_a))
    c.drawString(345,375,str(total_b))
    c.drawString(370.5,375,str(total_c))

    c.save(); packet.seek(0)

    overlay=PdfReader(packet)
    plantilla=PdfReader(open("plantilla.pdf","rb"))

    writer=PdfWriter()
    page=plantilla.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    año=datetime.today().year
    semana_num=datetime.today().isocalendar()[1]
    nombre=f"{usuario}_{año}_semana{semana_num}.pdf"

    with open(nombre,"wb") as f:
        writer.write(f)

    return send_file(nombre,as_attachment=True)

# ---------- WHATSAPP ----------
@app.route("/whatsapp")
def whatsapp():

    if not login_ok(): return redirect("/login")

    offset=int(request.args.get("semana",0))
    texto="Hola, te envío mi reporte semanal de horas."
    url=f"https://wa.me/?text={texto.replace(' ','%20')}"

    return f"""
<script>
window.onload=function(){{
window.location.href="/pdf?semana={offset}";
setTimeout(function(){{window.open("{url}","_blank");}},800);
}}
</script>
Generando PDF...
"""

# ---------- RUN ----------
if __name__=="__main__":
    app.run(debug=True)