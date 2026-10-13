import {LatestQuery,OperationKeys} from './state.mjs';
import {listView} from './lists.mjs';
import {tripDetail,observationHistory} from './details.mjs';
import {createTrip} from './forms.mjs';
export class Records {
  constructor(app) {this.app=app;this.page=new LatestQuery();this.operations=new OperationKeys();this.navigation=new Map();this.serial=0;this.timer=null;}
  leave() {this.serial++;this.page.cancel();clearTimeout(this.timer);this.timer=null;}
  clear() {this.leave();this.page.reset();this.operations.clear();this.navigation.clear();}
  list(kind) {listView(this,kind);}
  create() {createTrip(this);}
  detail(id) {tripDetail(this,id).catch(this.app.fail.bind(this.app));}
  history(observation) {observationHistory(this,observation).catch(this.app.fail.bind(this.app));}
}
