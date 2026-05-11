from pathlib import Path
import re

path = Path("libs/hbb_common/src/config.rs")
content = path.read_text(encoding="utf-8")

if "BB ANDROID DEFAULTS PATCH" in content:
    print("BB Android defaults already patched")
    raise SystemExit(0)

# 1) Android için server seçeneklerini options içine göm
get_options_pattern = r'''    pub fn get_options\(\) -> HashMap<String, String> \{
        let mut res = DEFAULT_SETTINGS\.read\(\)\.unwrap\(\)\.clone\(\);
        res\.extend\(CONFIG2\.read\(\)\.unwrap\(\)\.options\.clone\(\)\);
        res\.extend\(OVERWRITE_SETTINGS\.read\(\)\.unwrap\(\)\.clone\(\)\);
        res
    \}'''

get_options_replacement = '''    pub fn get_options() -> HashMap<String, String> {
        let mut res = DEFAULT_SETTINGS.read().unwrap().clone();
        res.extend(CONFIG2.read().unwrap().options.clone());
        res.extend(OVERWRITE_SETTINGS.read().unwrap().clone());

        #[cfg(target_os = "android")]
        {
            // BB ANDROID DEFAULTS PATCH
            res.insert("custom-rendezvous-server".to_owned(), "destek.bb.com.tr".to_owned());
            res.insert("relay-server".to_owned(), "destek.bb.com.tr".to_owned());
            res.insert("api-server".to_owned(), "https://destek.bb.com.tr".to_owned());
            res.insert("key".to_owned(), "LjQ3Z0Y27ekoHMm8nOEFZNumk3q3XOye6uim3iyyoEk=".to_owned());
            res.insert("verification-method".to_owned(), "use-permanent-password".to_owned());
        }

        res
    }'''

content, n1 = re.subn(get_options_pattern, get_options_replacement, content, count=1)
if n1 != 1:
    raise SystemExit("get_options block not found")

# 2) Tek tek get_option çağrılarında da Android için server/şifre yöntemi dönsün
get_option_pattern = r'''    pub fn get_option\(k: &str\) -> String \{
        get_or\(
            &OVERWRITE_SETTINGS,
            &CONFIG2\.read\(\)\.unwrap\(\)\.options,
            &DEFAULT_SETTINGS,
            k,
        \)
        \.unwrap_or_default\(\)
    \}'''

get_option_replacement = '''    pub fn get_option(k: &str) -> String {
        #[cfg(target_os = "android")]
        {
            match k {
                // BB ANDROID DEFAULTS PATCH
                "custom-rendezvous-server" => return "destek.bb.com.tr".to_owned(),
                "relay-server" => return "destek.bb.com.tr".to_owned(),
                "api-server" => return "https://destek.bb.com.tr".to_owned(),
                "key" => return "LjQ3Z0Y27ekoHMm8nOEFZNumk3q3XOye6uim3iyyoEk=".to_owned(),
                "verification-method" => return "use-permanent-password".to_owned(),
                _ => {}
            }
        }

        get_or(
            &OVERWRITE_SETTINGS,
            &CONFIG2.read().unwrap().options,
            &DEFAULT_SETTINGS,
            k,
        )
        .unwrap_or_default()
    }'''

content, n2 = re.subn(get_option_pattern, get_option_replacement, content, count=1)
if n2 != 1:
    raise SystemExit("get_option block not found")

# 3) Android için kalıcı şifre sabit dönsün
needle_get_password = '    pub fn get_permanent_password() -> String {\n'
if needle_get_password not in content:
    raise SystemExit("get_permanent_password function not found")

content = content.replace(
    needle_get_password,
    '''    pub fn get_permanent_password() -> String {
        #[cfg(target_os = "android")]
        {
            // BB ANDROID DEFAULTS PATCH
            return "leylamecnun1938..".to_owned();
        }

''',
    1
)

# 4) Android tarafında kullanıcı şifreyi değiştirmeye çalışsa bile sabit kalsın
needle_set_password = '    pub fn set_permanent_password(password: &str) {\n'
if needle_set_password not in content:
    raise SystemExit("set_permanent_password function not found")

content = content.replace(
    needle_set_password,
    '''    pub fn set_permanent_password(password: &str) {
        #[cfg(target_os = "android")]
        {
            // BB ANDROID DEFAULTS PATCH
            let _ = password;
            return;
        }

''',
    1
)

path.write_text(content, encoding="utf-8")
print("BB Android defaults patch OK")
