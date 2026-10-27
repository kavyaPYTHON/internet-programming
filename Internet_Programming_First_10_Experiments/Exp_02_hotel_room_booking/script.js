const records = [{"name": "Hotel Room Booking Item 1", "category": "Search rooms", "description": "Sample record for search rooms.", "price": 175}, {"name": "Hotel Room Booking Item 2", "category": "Check availability", "description": "Sample record for check availability.", "price": 250}, {"name": "Hotel Room Booking Item 3", "category": "Booking form", "description": "Sample record for booking form.", "price": 325}, {"name": "Hotel Room Booking Item 4", "category": "Booking history", "description": "Sample record for booking history.", "price": 400}];
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