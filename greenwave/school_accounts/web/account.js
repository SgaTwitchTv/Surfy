import {SessionState} from './portal/state.mjs';
import {API,errorText} from './portal/api.mjs';
import {Accounts} from './portal/auth.mjs';
import {Records} from './portal/records.mjs';
import {roleMenu} from './portal/roles.mjs';
import {RoleViews} from './portal/role_views.mjs';
import {action} from './portal/dom.mjs';
class Portal {
  constructor() {
    this.screen=document.querySelector('#screen');this.state=new SessionState();this.api=new API(this.state);
    this.active='login';this.accounts=new Accounts(this);this.records=new Records(this);this.roles=new RoleViews(this);
    this.state.listeners.add(value=>{this.api.abort();this.records.clear();this.roles.drafts.clear();for(const d of document.querySelectorAll('dialog')){d.close();d.remove();}
      this.accounts.linkToken=null;if(value)this.accounts.account();else{this.accounts.show('login');this.message('Zaloguj się, aby otworzyć własne dane.');}});
    window.addEventListener('hashchange',()=>this.accounts.link());
  }
  message(text) { document.querySelector('#message').textContent=text; }
  fail(error) { this.message(errorText(error)); }
  menu() {
    document.body.classList.toggle('signed-in',Boolean(this.state.value));
    const nav=document.querySelector('nav');nav.replaceChildren();
    const items=this.state.value?[['Moje przejazdy','trips'],['Moje obserwacje','observations'],...roleMenu(this.state.value.user.role),['Konto','account']]:[['Logowanie','login'],['Rejestracja','register'],['Reset hasła','request-reset']];
    for(const [label,name] of items) {const button=action(label,()=>{this.roles.drafts.clear();this.message('');if(name==='account')this.accounts.account();else if(['trips','observations'].includes(name))this.records.list(name);else if(name==='shared')this.records.list('trips','shared');else if(['users','audit','configs'].includes(name))this.roles.show(name);else this.accounts.show(name);},'nav-button');
      button.dataset.view=name;if(this.active===name)button.setAttribute('aria-current','page');nav.append(button);}
    document.querySelector('#identity').textContent=this.state.value?this.state.value.user.display_name+' · '+this.state.value.user.role:'Prywatny portal danych';
  }
  async init() {if(this.accounts.link())return;try{const data=await this.api.request('/auth/me');this.state.set(data);}catch{if(!this.state.value)this.accounts.show('login');}}
}
new Portal().init();
