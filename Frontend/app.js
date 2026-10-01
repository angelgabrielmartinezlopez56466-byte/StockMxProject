const API = window.STOCKMX_API || "http://127.0.0.1:8000";
const state = { token: localStorage.getItem("stockmx_token"), user: JSON.parse(localStorage.getItem("stockmx_user") || "null"), section: "dashboard", products: [], cart: [] };
const $ = (id) => document.getElementById(id);
const money = (value) => `$${Number(value || 0).toFixed(2)}`;
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[c]));
const omitEmpty = (data, fields) => Object.fromEntries(Object.entries(data).filter(([key, value]) => !fields.includes(key) || value !== ""));
const today = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; };
const daysAgo = (days) => { const date = new Date(); date.setDate(date.getDate() - days); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; };
function productOptions(products) {
  const options = products.filter((product) => product.activo).map((product) => {
    const unavailable = product.existencia_actual < 1;
    const availability = unavailable ? "Agotado" : `${product.existencia_actual} disponibles`;
    return `<option value="${product.id}" ${unavailable ? "disabled" : ""}>${esc(product.nombre)} · ${esc(product.codigo)} · ${availability}</option>`;
  }).join("");
  return `<option value="" selected disabled>Selecciona un producto</option>${options}`;
}
function toast(message) { $("toast").textContent = String(message?.message || message || "Ocurrió un error"); $("toast").classList.add("show"); setTimeout(() => $("toast").classList.remove("show"), 2600); }
async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}), ...(options.headers || {}) };
  const response = await fetch(API + path, { ...options, headers });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "No se pudo completar la operación");
  return body;
}
async function showApp() {
  $("login-view").classList.add("hidden"); $("app-view").classList.remove("hidden");
  $("user-badge").textContent = state.user.rol === "administrador" ? "Administrador" : "Empleado";
  document.querySelectorAll("[data-admin-only],.admin-action").forEach((el) => el.classList.toggle("hidden", state.user.rol !== "administrador"));
  showSection(state.section);
}
function showSection(section) {
  if (state.user?.rol !== "administrador" && section === "usuarios") section = "dashboard";
  state.section = section; document.querySelectorAll(".page-section").forEach((el) => el.classList.add("hidden"));
  $(`${section}-section`).classList.remove("hidden"); $("page-title").textContent = section === "dashboard" ? "Inicio" : section[0].toUpperCase() + section.slice(1);
  document.querySelectorAll("#main-nav button").forEach((el) => el.classList.toggle("active", el.dataset.section === section));
  const loaders = {dashboard:loadDashboard,productos:loadProducts,inventario:loadInventory,proveedores:loadSuppliers,usuarios:loadUsers,reportes:loadReports};
  loaders[section]?.();
}
function renderEmpty(text, colspan = 8) { return `<tr><td colspan="${colspan}" class="muted">${text}</td></tr>`; }
async function loadDashboard() {
  try {
    const [data, products] = await Promise.all([api("/dashboard"), api("/productos")]);
    state.products = products;
    $("sale-product").innerHTML = productOptions(products);
    updateSaleProductInfo();
    renderCart();
    $("dashboard-cards").innerHTML = `
      <div class="stat"><span>Productos activos</span><strong>${data.total_productos}</strong></div>
      <div class="stat alert"><span>Productos con stock bajo</span><strong>${data.productos_stock_bajo}</strong></div>`;
  } catch (error) {
    toast(error.message);
  }
}
async function loadProducts() {
  try { const search = $("product-search").value.trim(); const includeInactive = state.user.rol === "administrador" && $("include-inactive").checked; const params = new URLSearchParams({ incluir_inactivos: String(includeInactive) }); if (search) params.set("busqueda", search); state.products = await api(`/productos?${params}`); $("products-table").innerHTML = state.products.length ? state.products.map((p) => `<tr class="${p.activo ? "" : "inactive-row"}"><td>${esc(p.nombre)}</td><td>${esc(p.codigo)}</td><td>${money(p.precio)}</td><td>${p.existencia_actual}</td><td>${p.stock_minimo}</td><td><span class="badge ${p.activo ? (p.existencia_actual <= p.stock_minimo ? "low" : "") : "low"}">${p.activo ? (p.existencia_actual <= p.stock_minimo ? "Reponer":"Normal") : "Inactivo"}</span></td><td class="actions">${state.user.rol === "administrador" ? `<button class="secondary" onclick="editProduct(${p.id})">Editar</button>${p.activo ? `  <button class="danger" onclick="setProductActive(${p.id},false)">Eliminar</button>` : `<button class="secondary" onclick="setProductActive(${p.id},true)">Activar</button>`}` : ""}</td></tr>`).join("") : renderEmpty("No hay productos.", 7); } catch(e) { toast(e.message); }
}
async function loadInventory() {
  try { const low = $("low-stock-only").checked; const items = await api(`/inventario?solo_stock_bajo=${low}`); $("inventory-table").innerHTML = items.length ? items.map(p => `<tr><td>${esc(p.nombre)}</td><td>${esc(p.codigo)}</td><td>${p.existencia_actual}</td><td>${p.stock_minimo}</td><td><span class="badge ${p.stock_bajo?"low":""}">${p.stock_bajo?"Reponer":"Normal"}</span></td></tr>`).join("") : renderEmpty("No hay existencias.", 5); const [moves, products] = await Promise.all([api("/inventario/movimientos"), api("/productos")]); const names = Object.fromEntries(products.map((product) => [product.id, product.nombre])); $("movements-table").innerHTML = moves.slice(0,10).map(m => `<div class="cart-row"><span>${m.tipo} · ${esc(names[m.producto_id] || "Producto")} · ${m.motivo || "Sin motivo"}</span><strong>${m.cantidad}</strong></div>`).join("") || "<p class='muted'>Sin movimientos.</p>"; } catch(e) { toast(e.message); }
}
async function loadSuppliers() { try { const data = await api("/proveedores"); $("suppliers-table").innerHTML = data.map(p => `<tr><td>${esc(p.nombre)}</td><td>${esc(p.telefono)}</td><td>${esc(p.correo)}</td><td class="actions">${state.user.rol==="administrador"?`<button class="secondary" onclick="editSupplier(${p.id})">Editar</button><button class="danger" onclick="deleteSupplier(${p.id})">Eliminar</button>`:""}</td></tr>`).join("") || renderEmpty("No hay proveedores.", 4); } catch(e) { toast(e.message); } }
async function loadUsers() { if(state.user.rol !== "administrador") return; try { const data = await api("/usuarios"); $("users-table").innerHTML = data.map(u => `<tr><td>${esc(u.nombre)}</td><td>${esc(u.correo)}</td><td>${u.rol}</td><td><span class="badge ${u.activo?"":"low"}">${u.activo?"Activo":"Inactivo"}</span></td><td class="actions"><button class="secondary" onclick="editUser(${u.id})">Editar</button>${u.rol !== "administrador" && u.correo !== state.user.correo ? `<button class="${u.activo ? "danger" : "secondary"}" onclick="toggleUser(${u.id},${u.activo})">${u.activo ? "Eliminar" : "Activar"}</button>` : ""}</td></tr>`).join(""); } catch(e) { toast(e.message); } }
async function loadReports() {
  try {
    const query = new URLSearchParams();
    if ($("report-from").value) query.set("desde", $("report-from").value);
    if ($("report-to").value) query.set("hasta", $("report-to").value);
    const requests = [
      api(`/reportes/ventas?${query}`),
      api(`/reportes/productos-mas-vendidos?${query}`),
      api(`/reportes/productos-menos-vendidos?${query}`),
      api(`/reportes/ventas-detalle?${query}`),
    ];
    if (state.user.rol === "administrador") requests.push(api("/reportes/historial?limite=200"));
    const [sales, top, low, detail, history = []] = await Promise.all(requests);
    const units = detail.reduce((sum, row) => sum + row.cantidad, 0);
    const financial = state.user.rol === "administrador"
      ? `<div class="stat"><span>Ventas del periodo</span><strong>${money(sales.total_ventas)}</strong></div>`
      : "";
    $("report-cards").innerHTML = `${financial}
      <div class="stat"><span>Ventas realizadas</span><strong>${sales.cantidad_ventas}</strong></div>
      <div class="stat"><span>Unidades vendidas</span><strong>${units}</strong></div>`;
    $("top-products").innerHTML = top.map((product) => `
      <div class="cart-row"><span>${esc(product.nombre)} · ${product.unidades_vendidas} unidades</span>
      <strong>${state.user.rol === "administrador" ? money(product.ingresos) : `${product.unidades_vendidas} uds.`}</strong></div>`).join("")
      || "<p class='muted'>No hay ventas en el periodo.</p>";
    $("low-products").innerHTML = low.map((product) => `
      <div class="cart-row"><span>${esc(product.nombre)}</span><strong>${product.unidades_vendidas} unidades</strong></div>`).join("")
      || "<p class='muted'>Sin productos activos.</p>";
    $("report-detail").innerHTML = detail.map((row) => `
      <tr><td>#${row.venta_id}</td><td>${new Date(row.fecha).toLocaleString()}</td><td>${esc(row.producto)}</td>
      <td>${esc(row.codigo)}</td><td>${row.cantidad}</td><td>${money(row.precio_unitario)}</td><td>${money(row.subtotal)}</td></tr>`).join("")
      || renderEmpty("No hay operaciones en el periodo.", 7);
    $("report-preview").innerHTML = `
      <div class="preview-head"><strong>STOCK MX · REPORTE DE VENTAS</strong><span>${sales.desde} → ${sales.hasta}</span></div>
      <p>Detalle de ventas del periodo seleccionado.</p>`;
    if (state.user.rol === "administrador") {
      $("report-history").innerHTML = history.map((report) => `
        <div class="cart-row"><span>#${report.id} · ${report.rango_fechas} · ${new Date(report.fecha_generacion).toLocaleString()}</span>
        <strong>${money(report.total_ventas)}</strong></div>`).join("")
        || "<p class='muted'>No hay reportes guardados.</p>";
    }
  } catch (error) {
    toast(error.message);
  }
}
async function saveReport() { try { const query = new URLSearchParams({desde:$("report-from").value,hasta:$("report-to").value}); await api(`/reportes/ventas/generar?${query}`, {method:"POST"}); toast("Reporte guardado"); await loadReports(); } catch(e) { toast(e.message); } }
function supplierField(suppliers, value) { return {label:"Proveedor",name:"proveedor_id",required:false,value: value ?? "",options:[{value:"",label:"Sin proveedor"},...suppliers.map(s => ({value:s.id,label:s.nombre}))]}; }
function productPayload(data) { return {...data, precio:Number(data.precio), costo:Number(data.costo || 0), stock_minimo:Number(data.stock_minimo), proveedor_id:data.proveedor_id ? Number(data.proveedor_id) : null}; }
function openModal(title, fields, submit) { $("modal-title").textContent = title; $("modal-form").innerHTML = fields.map(f => `<label>${f.label}${f.options ? `<select name="${f.name}" ${f.required === false ? "" : "required"}>${f.options.map(o => `<option value="${o.value}" ${String(o.value) === String(f.value ?? "") ? "selected" : ""}>${esc(o.label)}</option>`).join("")}</select>` : `<input name="${f.name}" type="${f.type || "text"}" value="${esc(f.value || "")}" ${f.required === false ? "" : "required"}>`}</label>`).join("") + `<button class="primary" type="submit">Guardar</button>`; $("modal").classList.remove("hidden"); $("modal-form").onsubmit = async (event) => { event.preventDefault(); try { await submit(Object.fromEntries(new FormData(event.target))); $("modal").classList.add("hidden"); toast("Guardado correctamente"); showSection(state.section); } catch(e) { toast(e.message); } }; }
async function editProduct(id) { const p = state.products.find(x => x.id === id); const suppliers = await api("/proveedores"); openModal("Editar producto", [{label:"Nombre",name:"nombre",value:p.nombre},{label:"Código",name:"codigo",value:p.codigo},{label:"Precio de venta",name:"precio",type:"number",value:p.precio},{label:"Precio de adquisición",name:"costo",type:"number",value:p.costo},{label:"Categoría",name:"categoria",value:p.categoria,required:false},supplierField(suppliers,p.proveedor_id),{label:"Stock mínimo",name:"stock_minimo",type:"number",value:p.stock_minimo}], async d => api(`/productos/${id}`,{method:"PATCH",body:JSON.stringify(productPayload(d))})); }
async function setProductActive(id, active) { if (!active && !confirm("El producto se retirará del catálogo, pero conservará su historial. ¿Continuar?")) return; try { await api(`/productos/${id}`,{method:"PATCH",body:JSON.stringify({activo:active})}); toast(active ? "Producto activado" : "Producto eliminado"); loadProducts(); } catch(e) { toast(e.message); } }
async function editSupplier(id) { const p=(await api("/proveedores")).find(x=>x.id===id); openModal("Editar proveedor",[{label:"Nombre",name:"nombre",value:p.nombre},{label:"Teléfono",name:"telefono",value:p.telefono,required:false},{label:"Correo",name:"correo",type:"email",value:p.correo,required:false}],d=>api(`/proveedores/${id}`,{method:"PATCH",body:JSON.stringify(omitEmpty(d,["telefono","correo"]))})); }
async function deleteSupplier(id) { if (!confirm("Se eliminará este proveedor y cualquier relación con productos. ¿Continuar?")) return; try { await api(`/proveedores/${id}`, { method: "DELETE" }); toast("Proveedor eliminado"); loadSuppliers(); } catch (e) { toast(e.message); } }
async function editUser(id) { const u=(await api("/usuarios")).find(x=>x.id===id); openModal("Editar usuario",[{label:"Nombre",name:"nombre",value:u.nombre},{label:"Correo",name:"correo",type:"email",value:u.correo},{label:"Nueva contraseña",name:"password",type:"password",required:false}],d=>api(`/usuarios/${id}`,{method:"PATCH",body:JSON.stringify(omitEmpty(d,["password"]))})); }
async function toggleUser(id, active) { if (active && !confirm("El empleado será retirado del acceso al sistema. ¿Continuar?")) return; try { if (active) await api(`/usuarios/${id}`,{method:"DELETE"}); else await api(`/usuarios/${id}`,{method:"PATCH",body:JSON.stringify({activo:true})}); toast(active ? "Usuario eliminado" : "Usuario activado"); loadUsers(); } catch(e) { toast(e.message); } }
function updateSaleProductInfo() {
  const product = state.products.find((item) => item.id === Number($("sale-product").value));
  $("sale-product-info").textContent = product
    ? `${money(product.precio)} por unidad · ${product.existencia_actual} disponibles`
    : "Elige un producto para ver su precio y existencia.";
}
function addCart() {
  const product = state.products.find((item) => item.id === Number($("sale-product").value));
  const quantity = Number($("sale-quantity").value);
  const existing = state.cart.find((item) => item.producto_id === product?.id);
  if (!product || !Number.isInteger(quantity) || quantity < 1) {
    return toast("Selecciona un producto e indica una cantidad válida.");
  }
  if (quantity + (existing?.cantidad || 0) > product.existencia_actual) {
    return toast(`Solo hay ${product.existencia_actual} unidades disponibles de ${product.nombre}.`);
  }
  if (existing) existing.cantidad += quantity;
  else state.cart.push({ producto_id: product.id, nombre: product.nombre, precio: Number(product.precio), cantidad: quantity });
  $("sale-quantity").value = "1";
  $("sale-product").value = "";
  updateSaleProductInfo();
  renderCart();
}
function removeCartItem(index) {
  state.cart.splice(index, 1);
  renderCart();
}
function renderCart() {
  $("cart").innerHTML = state.cart.length
    ? state.cart.map((item, index) => `
      <div class="cart-row">
        <span><strong>${esc(item.nombre)}</strong><small>${item.cantidad} × ${money(item.precio)}</small></span>
        <span class="cart-item-total">${money(item.precio * item.cantidad)}<button class="danger cart-remove" type="button" aria-label="Quitar ${esc(item.nombre)}" onclick="removeCartItem(${index})">Quitar</button></span>
      </div>`).join("")
    : "<p class='muted cart-empty'>Agrega productos para comenzar la venta.</p>";
  $("cart-total").textContent = money(state.cart.reduce((sum, item) => sum + item.precio * item.cantidad, 0));
  $("confirm-sale").disabled = state.cart.length === 0;
}
async function movement(type) { try { const products=await api("/productos"); const options=products.map(p=>({value:p.id,label:`${p.nombre} · ${p.codigo} · stock ${p.existencia_actual}`})); const fields=[{label:"Producto",name:"producto_id",options},{label:"Cantidad",name:"cantidad",type:"number"},{label:"Motivo",name:"motivo",required:false}]; openModal(type==="entrada"?"Registrar entrada":"Registrar salida",fields, d=>api(`/inventario/${type==="entrada"?"entradas":"salidas"}`,{method:"POST",body:JSON.stringify({...d,producto_id:Number(d.producto_id),cantidad:Number(d.cantidad)})})); } catch (error) { toast(error.message); } }
function printReport() { document.body.classList.add("print-report"); window.print(); window.setTimeout(() => document.body.classList.remove("print-report"), 300); }
document.querySelectorAll("#main-nav button").forEach(b=>b.onclick=()=>showSection(b.dataset.section)); document.querySelectorAll("[data-refresh]").forEach(b=>b.onclick=()=>showSection(b.dataset.refresh)); $("sale-product").onchange=updateSaleProductInfo; $("login-form").onsubmit=async e=>{e.preventDefault();$("login-error").textContent="";try{const correo=$("login-email").value.trim();const d=await api("/auth/login",{method:"POST",body:JSON.stringify({correo,password:$("login-password").value})});state.token=d.access_token;state.user={nombre:d.nombre,correo,rol:d.rol};localStorage.setItem("stockmx_token",state.token);localStorage.setItem("stockmx_user",JSON.stringify(state.user));await showApp();}catch(err){$("login-error").textContent=err.message;}}; $("logout").onclick=()=>{localStorage.clear();location.reload()}; $("close-modal").onclick=()=>$("modal").classList.add("hidden"); $("search-products").onclick=loadProducts; $("product-search").onkeydown=e=>{if(e.key==="Enter")loadProducts()}; $("include-inactive").onchange=loadProducts; $("low-stock-only").onchange=loadInventory; $("new-entry").onclick=()=>movement("entrada"); $("new-exit").onclick=()=>movement("salida"); $("add-to-cart").onclick=addCart; $("confirm-sale").onclick=async()=>{if(!state.cart.length)return toast("El carrito está vacío");const button=$("confirm-sale");button.disabled=true;button.textContent="Registrando…";try{await api("/ventas",{method:"POST",body:JSON.stringify({detalles:state.cart.map(x=>({producto_id:x.producto_id,cantidad:x.cantidad}))})});state.cart=[];renderCart();$("sale-product").value="";updateSaleProductInfo();await loadDashboard();toast("Venta registrada");}catch(e){toast(e.message);button.disabled=false;}finally{button.textContent="Confirmar venta";}}; $("report-from").value=daysAgo(30); $("report-to").value=today(); $("load-reports").onclick=loadReports; $("save-report").onclick=saveReport; $("print-report").onclick=printReport; $("new-product").onclick=async()=>{try{const suppliers=await api("/proveedores");openModal("Nuevo producto",[{label:"Nombre",name:"nombre"},{label:"Código",name:"codigo"},{label:"Precio de venta",name:"precio",type:"number"},{label:"Precio de adquisición",name:"costo",type:"number",required:false},{label:"Categoría",name:"categoria",required:false},supplierField(suppliers),{label:"Stock mínimo",name:"stock_minimo",type:"number"},{label:"Existencia inicial",name:"existencia_inicial",type:"number"}],d=>api("/productos",{method:"POST",body:JSON.stringify({...productPayload(d),existencia_inicial:Number(d.existencia_inicial)})}));}catch(e){toast(e.message);}}; $("new-supplier").onclick=()=>openModal("Nuevo proveedor",[{label:"Nombre",name:"nombre"},{label:"Teléfono",name:"telefono",required:false},{label:"Correo",name:"correo",type:"email",required:false}],d=>api("/proveedores",{method:"POST",body:JSON.stringify(omitEmpty(d,["telefono","correo"]))})); $("new-user").onclick=()=>openModal("Nuevo usuario",[{label:"Nombre",name:"nombre"},{label:"Correo",name:"correo",type:"email"},{label:"Contraseña",name:"password",type:"password"},{label:"Rol (administrador o empleado)",name:"rol",value:"empleado"}],d=>api("/usuarios",{method:"POST",body:JSON.stringify(d)}));
const loginForm = $("login-form");
const submitLogin = loginForm.onsubmit;
loginForm.onsubmit = async (event) => {
  const button = loginForm.querySelector('[type="submit"]');
  const status = $("login-error");
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Conectando...";
  const slowConnectionNotice = window.setTimeout(() => {
    status.textContent = "Conectando…";
  }, 2500);
  try {
    await submitLogin(event);
  } finally {
    window.clearTimeout(slowConnectionNotice);
    button.disabled = false;
    button.textContent = originalLabel;
  }
};
async function restoreSession() {
  if (!state.token || !state.user) return;
  $("login-error").textContent = "Conectando para recuperar tu sesión...";
  const slowConnectionNotice = window.setTimeout(() => {
    $("login-error").textContent = "Conectando…";
  }, 2500);
  try {
    const profile = await api("/auth/me");
    state.user = profile;
    localStorage.setItem("stockmx_user", JSON.stringify(profile));
    await showApp();
  } catch (error) {
    localStorage.clear();
    $("login-error").textContent = "La sesión expiró. Inicia sesión nuevamente.";
  } finally {
    window.clearTimeout(slowConnectionNotice);
  }
}
restoreSession();
