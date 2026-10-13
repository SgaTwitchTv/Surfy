"""Transactional role operations and safe projections, separate from HTTP."""
import json
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.validation import text,email
from greenwave.school_data.errors import Conflict
from greenwave.school_resources.reads import pick, CONFIG_FIELDS, public_config
from greenwave.school_resources.policy import resource_id
from greenwave.school_records.writes import fields,revision
from greenwave.school_records.paging import Paging,dates
from .validation import payload

USER_FIELDS=('id','display_name','role','status','revision','created_at','updated_at','verified_email_at')
# Exact allowlist; private trip/observation/recording audit is never selected.
AUDIT_ACTIONS={'ACCOUNT_PROVISIONED','BOOTSTRAP_ADMIN','AUTH_LOGIN','AUTH_LOGOUT','AUTH_LOGOUT_ALL',
 'AUTH_VERIFY_EMAIL','AUTH_RESET','AUTH_PASSWORD_CHANGED','AUTH_REAUTH','ADMIN_ACCOUNT_CHANGED',
 'CONFIG_DRAFT_CREATED','CONFIG_DRAFT_EDITED','CONFIG_PUBLISHED','CONFIG_ARCHIVED','CONFIG_CHANGE_REASON'}


def user_dto(row):return {**pick(row,USER_FIELDS),'email':row['email_display']}
def config_dto(row):return {**pick(row,CONFIG_FIELDS),'creator_id':row['creator_id'],
 'payload':public_config(json.loads(row['payload'])),'publication_is_field_verification':False}


class Administration:
    def __init__(self,policy):
        self.policy,self.repo=policy,policy.repo
        self.paging=Paging(self.repo,policy.accounts.config.csrf_key)

    def accounts(self,raw,q):
        _,actor=self.policy.role(raw,{'ADMIN'})
        limit,_,page=self.paging.page(actor,'admin-users',q)
        clauses=['created_at<=?'];args=[page['as_of']]
        if 'email' in q:clauses.append('email_normalized=?');args.append(email(q['email']))
        for key,allowed in [('role',{'DRIVER','ANALYST','ADMIN'}),('status',{'ACTIVE','BLOCKED','PENDING_VERIFICATION'})]:
            if key in q:
                if q[key] not in allowed:raise AuthError(422,'VALIDATION')
                clauses.append(key+'=?');args.append(q[key])
        if page['last']:clauses.append('(created_at,id)<(?,?)');args.extend(page['last'])
        with self.repo.database.connection() as c:
            self.policy.session(raw,c);self.repo.user(c,actor,{'ADMIN'})
            rows=[dict(r) for r in c.execute('SELECT * FROM users WHERE '+' AND '.join(clauses)+' ORDER BY created_at DESC,id DESC LIMIT ?',(*args,limit+1))]
        rows,result=self.paging.result(rows,limit,page,'created_at')
        return {'items':[user_dto(r) for r in rows],'page':result}

    def account_change(self,raw,uid,body,request_id):
        self.policy.role(raw,{'ADMIN'},reauth=True)
        fields(body,{'expected_revision','reason'},{'role','status'})
        if not ({'role','status'} & body.keys()):raise AuthError(422,'VALIDATION')
        revision(body['expected_revision']);text(body['reason'],3,500)
        if body.get('status','ACTIVE') not in {'ACTIVE','BLOCKED'}:raise AuthError(422,'VALIDATION')
        with self.repo.atomic(request_id) as (repo,c):
            _,actor=self.policy.session(raw,c)
            target=repo.change_account(actor,resource_id(uid),body['expected_revision'],role=body.get('role'),status=body.get('status'),reason=body['reason'])
        self.policy.accounts.credentials_changed()
        return user_dto(target)

    def audit(self,raw,q):
        _,actor=self.policy.role(raw,{'ADMIN'})
        limit,_,page=self.paging.page(actor,'admin-audit',q)
        clauses=["resource_type IN ('USER','CONFIG')",'server_at<=?','action IN ('+','.join('?' for _ in AUDIT_ACTIONS)+')'];args=[page['as_of'],*sorted(AUDIT_ACTIONS)]
        after,before=dates(q)
        for col,op,v in [('server_at','>=',after),('server_at','<',before),('actor_id','=',resource_id(q['actor']) if 'actor' in q else None),('action','=',q.get('action'))]:
            if v is not None:
                if col=='action' and v not in AUDIT_ACTIONS:raise AuthError(422,'VALIDATION')
                clauses.append(col+op+'?');args.append(v)
        if page['last']:clauses.append('(server_at,sequence)<(?,?)');args.extend([page['last'][0],int(page['last'][1],16)])
        with self.repo.database.connection() as c:
            self.policy.session(raw,c);self.repo.user(c,actor,{'ADMIN'})
            rows=[dict(r) for r in c.execute('SELECT sequence,actor_id,action,resource_type,resource_id,server_at,outcome,CASE WHEN action IN (\'ADMIN_ACCOUNT_CHANGED\',\'CONFIG_CHANGE_REASON\',\'CONFIG_ARCHIVED\') THEN reason ELSE \'\' END AS reason FROM audit_events WHERE '+' AND '.join(clauses)+' ORDER BY server_at DESC,sequence DESC LIMIT ?',(*args,limit+1))]
        for r in rows:r['id']=f"{r['sequence']:032x}"
        rows,result=self.paging.result(rows,limit,page,'server_at')
        return {'items':[{k:v for k,v in r.items() if k!='id'} for r in rows],'page':result}

    def config_write(self,raw,cid,operation,body,request_id):
        self.policy.role(raw,{'ADMIN'} if operation in {'publish','archive'} else {'ADMIN','ANALYST'},reauth=operation in {'publish','archive'})
        required={'kind','logical_id','payload','reason'} if operation=='create' else {'expected_revision','reason','payload'} if operation=='edit' else {'expected_revision','reason'} if operation=='publish' else {'reason'}
        fields(body,required,{'base_version_id'} if operation=='create' else ())
        text(body['reason'],3,500)
        if 'expected_revision' in body:revision(body['expected_revision'])
        with self.repo.atomic(request_id) as (repo,c):
            _,actor=self.policy.session(raw,c)
            if operation=='create':
                if body.get('base_version_id'):
                    base=c.execute('SELECT kind,logical_id FROM config_versions WHERE id=?',(resource_id(body['base_version_id']),)).fetchone()
                    if not base or base['kind']!=body['kind'] or base['logical_id']!=body['logical_id']:raise AuthError(422,'VALIDATION')
                row=repo.create_config(actor,body['kind'],body['logical_id'],payload(body['kind'],body['payload']))
            else:
                old=c.execute('SELECT * FROM config_versions WHERE id=?',(resource_id(cid),)).fetchone()
                if not old:raise AuthError(404,'NOT_FOUND')
                if operation=='edit':row=repo.edit_config(actor,cid,body['expected_revision'],payload(old['kind'],body['payload']))
                elif operation=='publish':
                    payload(old['kind'],json.loads(old['payload']),stored=True)
                    row=repo.publish_config(actor,cid,body['expected_revision'])
                else:
                    repo.user(c,actor,{'ADMIN'},reauth=True)
                    if old['status']!='ARCHIVED':
                        c.execute("UPDATE config_versions SET status='ARCHIVED',revision=revision+1 WHERE id=?",(cid,))
                        repo.audit(c,actor,'CONFIG_ARCHIVED','CONFIG',cid,body['reason'])
                    return None
            repo.audit(c,actor,'CONFIG_CHANGE_REASON','CONFIG',row['id'],body['reason'])
            return config_dto(row)
