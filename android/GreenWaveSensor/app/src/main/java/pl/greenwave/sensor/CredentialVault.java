package pl.greenwave.sensor;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Device bearer encrypted with a non-exportable Android Keystore key. No backup. */
final class CredentialVault {
    private static SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if (!store.containsAlias("greenwave-school-device")) {
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder("greenwave-school-device",KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            generator.generateKey();
        }
        return (SecretKey)store.getKey("greenwave-school-device",null);
    }
    static synchronized void write(Context context,String token) {
        try {
            if (token.isEmpty()) {ConfigStore.prefs(context).edit().remove("device_cipher").remove("device_iv").apply();return;}
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());
            ConfigStore.prefs(context).edit().putString("device_cipher",Base64.encodeToString(cipher.doFinal(token.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP))
                .putString("device_iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)).apply();
        } catch (Exception error) {throw new IllegalStateException("Nie można bezpiecznie zapisać parowania");}
    }
    static synchronized String read(Context context) {
        try {
            String data=ConfigStore.prefs(context).getString("device_cipher","");if(data.isEmpty())return "";
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(ConfigStore.prefs(context).getString("device_iv",""),Base64.NO_WRAP)));
            return new String(cipher.doFinal(Base64.decode(data,Base64.NO_WRAP)),StandardCharsets.UTF_8);
        } catch (Exception error) {return "";}
    }
    private CredentialVault() {}
}
