import {validate} from './validation.mjs';
import {errorText} from './api.mjs';
let sequence=0;
export function el(tag,text='',className='') { const n=document.createElement(tag);n.textContent=text;n.className=className;return n; }
export function action(label,fn,kind='secondary') { const b=el('button',label,kind);b.type='button';b.addEventListener('click',fn);return b; }
export function notice(text) { const n=el('p',text,'notice');n.setAttribute('role','status');n.setAttribute('aria-live','polite');return n; }
export function field(form,{name,label,type='text',value='',options,max,required=true}) {
  const wrap=el('label',label),id='field-'+(++sequence),input=el(options?'select':type==='textarea'?'textarea':'input');
  input.id=id;input.name=name;input.required=required;
  if(input.tagName==='INPUT') input.type=type;
  if(max) input.maxLength=max;
  if(options) for(const [v,t] of options) { const o=el('option',t);o.value=v;input.append(o); }
  input.value=value || (options&&!options.some(o=>o[0]==='')?options[0][0]:'');const error=el('span','','error');error.id=id+'-error';error.dataset.error=name;
  input.setAttribute('aria-describedby',error.id);wrap.htmlFor=id;wrap.append(input,error);form.append(wrap);return input;
}
export function form(specs,rules,submit,label='Zapisz') {
  const node=el('form');node.noValidate=true;for(const spec of specs) field(node,spec);
  const feedback=notice(''),button=el('button',label,'primary');button.type='submit';node.append(feedback,button);
  const setErrors=errors=>{for(const span of node.querySelectorAll('[data-error]')) { const name=span.dataset.error;span.textContent=errors[name]||'';node.elements.namedItem(name).setAttribute('aria-invalid',String(Boolean(errors[name]))); }};
  node.addEventListener('submit',async event=>{
    event.preventDefault();if(node.dataset.busy==='true') return;
    const body=Object.fromEntries(new FormData(node));const errors=validate(body,rules);setErrors(errors);
    if(Object.keys(errors).length) { node.querySelector('[aria-invalid=true]')?.focus();return; }
    node.dataset.busy='true';button.disabled=true;feedback.textContent='Trwa operacja…';
    try { const outcome=await submit(body,node,feedback);if(node.isConnected&&outcome!==false) feedback.textContent=typeof outcome==='string'?outcome:'Zapisano.'; }
    catch(error) { if(node.isConnected) { feedback.textContent=typeof error.status==='number'?errorText(error):error.name==='AbortError'?'Przerwano żądanie. Wynik zapisu może być nieznany; nie zmieniaj operacji przy retry.':error.message;setErrors(error.fields||{}); } }
    finally { node.dataset.busy='false';button.disabled=false; }
  });return node;
}
export function dialog(title,content) {
  const previous=document.activeElement,node=el('dialog'),heading=el('h2',title);heading.id='dialog-'+(++sequence);
  node.setAttribute('aria-labelledby',heading.id);node.append(heading,content,action('Zamknij',()=>node.close()));document.body.append(node);
  node.addEventListener('close',()=>{node.remove();if(previous?.isConnected) previous.focus();else document.querySelector('nav button[aria-current=page]')?.focus();});
  node.showModal();return node;
}
export function table(headers,rows) {
  const wrap=el('div','','table-scroll');wrap.tabIndex=0;wrap.setAttribute('aria-label','Tabela danych; przewijanie poziome');
  const node=el('table'),head=el('thead'),tr=el('tr');for(const label of headers) { const th=el('th',label);th.scope='col';tr.append(th); }head.append(tr);
  const body=el('tbody');for(const cells of rows) { const row=el('tr');for(const value of cells) { const td=el('td');td.append(value instanceof Node?value:document.createTextNode(String(value)));row.append(td); }body.append(row); }
  node.append(head,body);wrap.append(el('p','Przesuń tabelę w poziomie, aby odczytać wszystkie kolumny i akcje.','table-hint'),node);return wrap;
}
