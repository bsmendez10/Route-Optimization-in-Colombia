'use strict';
const $ = id => document.getElementById(id);
const {stops, minutes} = window.demoPlan;
const deliveries = stops.filter(stop => stop.order > 0 && stop.order < stops.length - 1);
const key = 'enviar-portfolio-route-progress-v1';
let done = new Set();
try {
  const saved = JSON.parse(localStorage.getItem(key) || '[]');
  if (Array.isArray(saved)) done = new Set(deliveries.filter(s => saved.includes(s.id)).map(s => s.id));
} catch {
  $('storage-note').textContent = 'Progress is available for this session.';
}
let selected = deliveries[0].id;
const svg = $('map');
function draw(tag, attrs, parent = svg) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  parent.append(node);
  return node;
}
function position(order) {
  const row = Math.floor(order / 7);
  const col = order % 7;
  return [50 + (row % 2 ? 6 - col : col) * 86, 65 + row * 125 + (col % 2) * 15];
}
for (let y = 20; y < 380; y += 24) {
  for (let x = 22; x < 620; x += 24) draw('circle', {cx:x, cy:y, r:1.2, fill:'#c6d7ce'});
}
draw('polyline', {points:stops.map(s => position(s.order).join(',')).join(' '), fill:'none', stroke:'#087166', 'stroke-width':4, 'stroke-linejoin':'round'});
const markers = new Map();
for (const stop of stops) {
  const [x,y] = position(stop.order);
  const label = stop.order === 0 ? 'A' : stop.order === stops.length - 1 ? 'B' : String(stop.order).padStart(2,'0');
  const g = draw('g', {transform:'translate('+x+' '+y+')', tabindex:0, role:'button', 'aria-label':label+' '+stop.name});
  draw('title', {}, g).textContent = stop.name;
  draw('circle', {r:17}, g);
  draw('text', {}, g).textContent = label;
  g.addEventListener('click', () => select(stop.id));
  g.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(stop.id); }
  });
  markers.set(stop.id,g);
}
function select(id) {
  selected = id;
  renderSelection();
}
function renderSelection() {
  const stop = stops.find(s => s.id === selected);
  const title = document.createElement('strong');
  title.textContent = stop.name;
  const detail = document.createElement('p');
  detail.textContent = stop.order === 0 ? 'Start of the route.'
    : stop.minutes + ' min from ' + stops[stop.order-1].name + (deliveries.includes(stop) ? ' · ' + (done.has(stop.id) ? 'Completed' : 'Pending') : ' · End of the route');
  $('detail').replaceChildren(title,detail);
  for (const s of stops) {
    const marker = markers.get(s.id);
    marker.setAttribute('class', ['marker', deliveries.includes(s) ? '' : 'endpoint', done.has(s.id) ? 'done' : '', selected === s.id ? 'selected' : ''].join(' '));
    marker.setAttribute('aria-pressed', String(selected === s.id));
  }
}
function renderList() {
  const list = $('list');
  list.replaceChildren();
  const filter = $('filter').value;
  for (const stop of deliveries) {
    const completed = done.has(stop.id);
    if (filter !== 'all' && completed !== (filter === 'done')) continue;
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = String(stop.order).padStart(2,'0') + '  ' + stop.name;
    button.addEventListener('click', () => select(stop.id));
    const label = document.createElement('label');
    const check = document.createElement('input');
    check.type = 'checkbox';
    check.checked = completed;
    check.dataset.id = stop.id;
    check.setAttribute('aria-label', 'Mark '+stop.name+' complete');
    check.addEventListener('change', () => {
      if (check.checked) done.add(stop.id); else done.delete(stop.id);
      try { localStorage.setItem(key,JSON.stringify([...done])); }
      catch { $('storage-note').textContent = 'Progress is available for this session.'; }
      renderProgress();
      renderSelection();
      if (filter !== 'all') { renderList(); $('filter').focus(); }
    });
    label.append(check,' Done');
    li.append(button,label);
    list.append(li);
  }
  if (!list.children.length) {
    const empty = document.createElement('li');
    empty.textContent = 'No deliveries match this filter.';
    list.append(empty);
  }
}
function renderProgress() {
  $('count').textContent = done.size+' of '+deliveries.length;
  $('progress').max = deliveries.length;
  $('progress').value = done.size;
}
$('deliveries').textContent = deliveries.length;
$('legs').textContent = stops.length - 1;
$('minutes').textContent = minutes;
$('filter').addEventListener('change',renderList);
renderProgress();
renderSelection();
renderList();
