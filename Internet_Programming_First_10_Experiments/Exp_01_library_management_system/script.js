const records = [{"name": "Library Management System Item 1", "category": "Search books", "description": "Sample record for search books.", "price": 175}, {"name": "Library Management System Item 2", "category": "Book catalogue", "description": "Sample record for book catalogue.", "price": 250}, {"name": "Library Management System Item 3", "category": "Borrowing history", "description": "Sample record for borrowing history.", "price": 325}, {"name": "Library Management System Item 4", "category": "Admin: add/update books", "description": "Sample record for admin: add/update books.", "price": 400}];
const items = document.querySelector("#items");
const search = document.querySelector("#search");
const filter = document.querySelector("#filter");
function render() {
  const q = search.value.trim().toLowerCase();
  const cat = filter.value;
  const shown = records.filter(x => (x.name+" "+x.category+" "+x.description).toLowerCase().includes(q) && (!cat || x.category===cat));
  document.querySelector("#count").textContent = `${shown.length} record(s)`;
  items.innerHTML = shown.length ? shown.map((x,i)=>`<article class="item"><h3>${x.name}</h3><p>${x.category}</p><p>${x.description}</p><div class="price">₹${x.price.toFixed(2)}</div><button type="button" data-name="${x.name}">View details</button></article>`).join("") : '<p class="muted">No matching records. Try another search.</p>';
}
search.addEventListener("input",render);
filter.addEventListener("change",render);
items.addEventListener("click",e=>{const b=e.target.closest("button[data-name]");if(b) alert("Sample record: "+b.dataset.name+"\n\nConnect this action to your required experiment logic.");});
document.querySelector("#demoForm").addEventListener("submit",e=>{e.preventDefault();const data=new FormData(e.currentTarget);document.querySelector("#message").textContent=`Thanks, ${data.get("name")}. Demo form validated successfully (not saved to a server).`;e.currentTarget.reset();});
render();