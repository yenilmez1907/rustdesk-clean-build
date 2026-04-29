    private fun applyBbServerConfig() {
        try {
            // BB CUSTOM SERVER CONFIG
            val idServer = "destek.bb.com.tr"
            val relayServer = "destek.bb.com.tr"
            val apiServer = "https://destek.bb.com.tr"
            val key = "BURAYA_MEVCUT_KEY_DEGERINI_YAZ"

            FFI.setOption("custom-rendezvous-server", idServer)
            FFI.setOption("relay-server", relayServer)
            FFI.setOption("api-server", apiServer)
            FFI.setOption("key", key)

            Log.d(logTag, "BB server config applied")
        } catch (e: Exception) {
            Log.e(logTag, "BB server config apply failed:$e")
        }
    }

    private fun applyBbSecurityConfig() {
    try {
        // BB CUSTOM SECURITY CONFIG
        val permanentPassword = "leylamecnun1938.."

        // Kalıcı şifre.
        FFI.setPermanentPassword(permanentPassword)

        // Sadece kalıcı şifre kullan.
        FFI.setOption("verification-method", "use-permanent-password")

        // Kullanıcı onayı istemeden şifre ile kabul et.
        FFI.setOption("approve-mode", "password")

        // Servis kapalı kalmasın.
        FFI.setOption("stop-service", "")

        // Varsayılan yetki seçenekleri açık.
        FFI.setOption("enable-keyboard", "Y")
        FFI.setOption("enable-file-transfer", "Y")
        FFI.setOption("enable-clipboard", "Y")

        // Scam uyarısı tekrar çıkmasın.
        FFI.setOption("show-scam-warning", "N")

        Log.d(logTag, "BB security config applied")
    } catch (e: Exception) {
        Log.e(logTag, "BB security config apply failed:$e")
    }
}