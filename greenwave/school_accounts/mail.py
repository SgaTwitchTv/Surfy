import queue
import smtplib
import ssl
import threading
from email.message import EmailMessage


class Mailer:
    """Bounded volatile queue. Raw tokens never enter DB/outbox/audit/logs."""
    def __init__(self,repo,config,capacity=100,transport=None):
        self.repo,self.config=repo,config
        self.slots=threading.BoundedSemaphore(capacity)
        self.queue=queue.Queue()
        self.transport=transport or self.smtp
        self.thread=threading.Thread(target=self.run,name='school-smtp',daemon=True)
        self.thread.start()

    def reserve(self):
        return self.slots.acquire(blocking=False)

    def release(self):
        self.slots.release()

    def submit(self,token_id,address,purpose,raw):
        self.queue.put((token_id,address,purpose,raw))

    def smtp(self,message):
        cfg=self.config
        if cfg.smtp_mode=='smtps':
            client=smtplib.SMTP_SSL(cfg.smtp_host,cfg.smtp_port,timeout=5,context=ssl.create_default_context())
        else:
            client=smtplib.SMTP(cfg.smtp_host,cfg.smtp_port,timeout=5)
        with client:
            if cfg.smtp_mode=='starttls':client.starttls(context=ssl.create_default_context())
            if cfg.smtp_user:client.login(cfg.smtp_user,cfg.smtp_password)
            client.send_message(message)

    def run(self):
        while True:
            job=self.queue.get()
            if job is None:
                self.queue.task_done();return
            token_id,address,purpose,raw=job
            state='FAILED'
            try:
                with self.repo.database.transaction(False) as c:
                    active=c.execute("SELECT 1 FROM account_tokens WHERE id=? AND delivery_state='PENDING' AND revoked_at IS NULL AND expiry>?",(token_id,self.repo.clock())).fetchone()
                if active:
                    message=EmailMessage()
                    message['From']=self.config.smtp_sender;message['To']=address
                    message['Subject']='GreenWave: aktywacja konta' if purpose=='VERIFY_EMAIL' else 'GreenWave: reset hasła'
                    action='verify' if purpose=='VERIFY_EMAIL' else 'reset'
                    message.set_content('Otwórz link i potwierdź operację w GreenWave.\n'+self.config.base_url.rstrip('/')+'/#'+action+'='+raw+'\nNie przekazuj tego linku innym osobom.')
                    self.transport(message)
                    state='SENT'
            except Exception:
                # Never interpolate SMTP exception/message/token into logs or audit.
                state='FAILED'
            finally:
                with self.repo.database.transaction() as c:
                    c.execute("UPDATE account_tokens SET delivery_state=?,revoked_at=CASE WHEN ?='FAILED' THEN COALESCE(revoked_at,?) ELSE revoked_at END WHERE id=?",(state,state,self.repo.clock(),token_id))
                self.slots.release();self.queue.task_done()
                raw=message=None

    def close(self):
        self.queue.put(None)
        self.thread.join(timeout=40)
        if self.thread.is_alive():
            raise RuntimeError('SMTP worker did not stop within its transport timeout')
