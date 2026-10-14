import {el,action,form,notice} from './dom.mjs';
import {rules} from './validation.mjs';
const definitions={login:['Logowanie',[['email','Email','email'],['password','Hasło','password']]],register:['Utwórz konto kierowcy',[['display_name','Nazwa','text'],['email','Email','email'],['password','Hasło','password'],['password_confirmation','Powtórz hasło','password']]],'request-reset':['Odzyskaj dostęp',[['email','Email','email']]],'reset-password':['Ustaw nowe hasło',[['password','Nowe hasło','password'],['password_confirmation','Powtórz hasło','password']]],'change-password':['Zmień hasło',[['current_password','Obecne hasło','password'],['new_password','Nowe hasło','password'],['password_confirmation','Powtórz nowe hasło','password']]],reauth:['Potwierdź tożsamość',[['password','Hasło','password']]],'verify-email':['Aktywacja email',[]]};
export class Accounts {
  constructor(app) { this.app=app;this.linkToken=null; }
  link() { const p=new URLSearchParams(location.hash.slice(1));const kind=p.has('reset')?'reset':p.has('verify')?'verify':null;
    history.replaceState(null,'',location.pathname);if(!kind)return false;
    this.app.state.clear();this.linkToken=p.get(kind);this.show(kind==='reset'?'reset-password':'verify-email');return true;
  }
  show(target='login') {
    if(target!=='reauth')this.app.roles.drafts.clear();
    this.app.records.leave();this.app.active=target;this.app.menu();
    const screen=this.app.screen;screen.replaceChildren();const [title,fields]=definitions[target];screen.append(el('p','Dostęp do Twoich danych','eyebrow'),el('h2',title));
    const validation={},specs=fields.map(([name,label,type])=>{validation[name]=name==='password_confirmation'?(v,b)=>v===(b.new_password||b.password)?'':'Hasła muszą być identyczne.':rules[name]||rules.password;
      return {name,label,type,max:type==='password'?256:name==='email'?254:80};});
    const node=form(specs,validation,async body=>{
      if(!this.app.state.value) this.app.state.preauth=await this.app.api.request('/auth/preflight');
      if(['verify-email','reset-password'].includes(target)) { if(!/^[A-Za-z0-9_-]{43}$/.test(this.linkToken||''))throw new Error('Otwórz poprawny link z poczty.');body.token=this.linkToken; }
      let data;try{data=await this.app.api.request('/auth/'+target,{method:'POST',body});}finally{if(target==='reauth')node.elements.password.value='';}
      if(['login','reauth'].includes(target)) { const pending=target==='reauth'?this.app.roles.drafts.take(data.user.id):null;this.app.state.set(data);this.app.message('Zalogowano.');if(pending)await this.app.roles.resume(pending); }
      else if(['change-password','reset-password'].includes(target)) { this.linkToken=null;this.app.state.clear();this.app.message('Operacja zakończona. Zaloguj się ponownie.'); }
      else if(target==='verify-email') {this.linkToken=null;this.show('login');this.app.message('Konto aktywne. Zaloguj się.');}
      else {this.show('login');this.app.message(data.message+' Sprawdź pocztę.');}
    },target==='verify-email'?'Potwierdź aktywację':'Potwierdź');
    for(const input of node.querySelectorAll('input'))input.autocomplete=input.type==='password'?(['register','reset-password'].includes(target)||input.name==='new_password'||input.name==='password_confirmation'?'new-password':'current-password'):input.name==='email'?'email':'nickname';
    screen.append(node);
    if(target==='reauth'){
      const cancel=()=>{this.app.roles.drafts.clear();this.account();document.querySelector('nav [data-view=account]')?.focus();};
      if(this.app.roles.drafts.has(this.app.state.value?.user.id))node.append(action('Zrezygnuj z powrotu',cancel));
      node.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();cancel();}});
      requestAnimationFrame(()=>{if(node.isConnected)node.elements.password.focus();});
    }
    if(target==='verify-email')screen.append(notice('Samo otwarcie linku nie aktywuje konta. Potwierdź przyciskiem.'));
    if(this.app.state.value)screen.append(action('Powrót do konta',()=>this.account()));
  }
  account() {
    this.app.roles.drafts.clear();
    this.app.records.leave();this.app.active='account';this.app.menu();const screen=this.app.screen,user=this.app.state.value.user;
    screen.replaceChildren(el('p','Ustawienia i bezpieczeństwo','eyebrow'),el('h2','Twoje konto'));
    const dl=el('dl');for(const [name,value] of [['Nazwa',user.display_name],['Email',user.email],['Rola',user.role]])dl.append(el('dt',name),el('dd',value));screen.append(dl);
    screen.append(notice('Każda rola ma własne dane. Rola administratora nie daje dostępu do cudzych przejazdów. Dodatkowe widoki wynikają z bieżącej roli; publikacja konfiguracji nie potwierdza danych terenowych.'));
    const actions=el('div','','actions');for(const [label,target] of [['Zmień hasło','change-password'],['Potwierdź tożsamość','reauth'],['Wyloguj','logout'],['Wyloguj wszystkie sesje','logout-all']])actions.append(action(label,async()=>{
      if(!target.startsWith('logout')) {this.show(target);return;}
      const button=actions.querySelectorAll('button');button.forEach(b=>b.disabled=true);
      try {await this.app.api.request('/auth/'+target,{method:'POST',body:{}});this.app.state.clear();this.app.message('Wylogowano.');}
      catch(error){this.app.fail(error);}finally{button.forEach(b=>b.disabled=false);}
    }));screen.append(actions);
  }
}
