from pathlib import Path
import re

path = Path("libs/hbb_common/src/config.rs")
content = path.read_text(encoding="utf-8")

if "BB CUSTOM SERVER CONFIG" in content:
    print("BB embedded Android server config already patched")
    raise SystemExit(0)

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
            // BB CUSTOM SERVER CONFIG
            res.insert("custom-rendezvous-server".to_owned(), "destek.bb.com.tr".to_owned());
            res.insert("relay-server".to_owned(), "destek.bb.com.tr".to_owned());
            res.insert("api-server".to_owned(), "https://destek.bb.com.tr".to_owned());
            res.insert("key".to_owned(), "LjQ3Z0Y27ekoHMm8nOEFZNumk3q3XOye6uim3iyyoEk=".to_owned());
        }

        res
    }'''

content, n1 = re.subn(get_options_pattern, get_options_replacement, content, count=1)
if n1 != 1:
    raise SystemExit("get_options block not found for embedded config patch")

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
                // BB CUSTOM SERVER CONFIG
                "custom-rendezvous-server" => return "destek.bb.com.tr".to_owned(),
                "relay-server" => return "destek.bb.com.tr".to_owned(),
                "api-server" => return "https://destek.bb.com.tr".to_owned(),
                "key" => return "LjQ3Z0Y27ekoHMm8nOEFZNumk3q3XOye6uim3iyyoEk=".to_owned(),
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
    raise SystemExit("get_option block not found for embedded config patch")

path.write_text(content, encoding="utf-8")
print("BB embedded Android server config patch OK")
