import os
import json
import msal
import requests
from typing import Optional, Dict, Any
from pathlib import Path

class DelegatedGraphService:
    def __init__(
        self,
        client_id: str,
        authority: str,
        scopes: list[str],
        token_cache_path: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize the DelegatedGraphService with OAuth2 client configuration.
        
        Args:
            client_id: Azure AD application client ID
            authority: Authority URL (e.g., 'https://login.microsoftonline.com/your-tenant-id')
            scopes: List of Microsoft Graph API scopes (e.g., ['Mail.Send', 'User.Read'])
            token_cache_path: Optional path to store the token cache
            client_secret: Optional client secret for confidential client flow
        """
        self.client_id = client_id
        self.authority = authority
        self.scopes = (
            scopes if isinstance(scopes, list)
            else [s for s in str(scopes or "").replace(",", " ").split() if s]
        )
        self.client_secret = client_secret
        self.token_cache = msal.SerializableTokenCache()
        self.token_cache_path = token_cache_path or "./.msal_token_cache.json"
        
        # Load token cache if it exists
        if os.path.exists(self.token_cache_path):
            try:
                with open(self.token_cache_path, "r") as f:
                    self.token_cache.deserialize(f.read())
            except Exception as e:
                print(f"Warning: Could not load token cache: {e}")
                self.token_cache = msal.SerializableTokenCache()
        
        # Initialize the MSAL application
        if self.client_secret:
            print("client secret service", self.client_secret)
            # Use ConfidentialClientApplication for server-side flows
            self.scopes = ["https://graph.microsoft.com/.default"]
            self.app = msal.ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=authority,
                token_cache=self.token_cache
            )
        else:
            # Use PublicClientApplication for device code flow
            self.scopes = [s for s in self.scopes if "://" not in s and not s.endswith("/.default")]
            if not self.scopes:
                self.scopes = ["Mail.Send", "User.Read"]
            self.app = msal.PublicClientApplication(
                client_id=client_id,
                authority=authority,
                token_cache=self.token_cache
            )
    
    def _save_token_cache(self):
        """Save the token cache to a file with proper error handling."""
        if not self.token_cache_path:
            return
            
        try:
            # Create parent directories if they don't exist
            cache_dir = os.path.dirname(self.token_cache_path)
            if cache_dir:  # Only create directory if path is not in current directory
                os.makedirs(cache_dir, exist_ok=True)
            
            # Write with 'w' mode to create or truncate the file
            with open(self.token_cache_path, "w") as f:
                f.write(self.token_cache.serialize())
                
        except Exception as e:
            print(f"Warning: Could not save token cache: {e}")
            # Print the full path for debugging
            print(f"Attempted to save to: {os.path.abspath(self.token_cache_path)}")
    
    def _get_token(self) -> Optional[str]:
        """
        Get an access token for the Graph API using delegated permissions.
        
        Returns:
            str: Access token if successful
            
        Raises:
            Exception: If token acquisition fails with detailed error information
        """
        print("\n=== Iniciando proceso de autenticación ===")
        print(f"Scopes: {self.scopes}")
        print(f"Authority: {self.authority}")
        
        try:
            # Try to get a token from cache
            print("\nBuscando token en caché...")
            accounts = self.app.get_accounts()
            print(f"Cuentas encontradas: {len(accounts)}")
            
            if accounts:
                print(f"Intentando autenticación silenciosa para la cuenta: {accounts[0]['username']}")
                result = self.app.acquire_token_silent(
                    scopes=self.scopes,
                    account=accounts[0]
                )
                
                if result and "access_token" in result:
                    print("¡Token obtenido del caché exitosamente!")
                    return result["access_token"]
                else:
                    print("No se pudo obtener un token del caché. Iniciando flujo de autenticación interactiva...")
            else:
                print("No se encontraron cuentas en caché. Iniciando flujo de autenticación interactiva...")
            
            # Iniciar flujo de autenticación con dispositivo
            if self.client_secret:
                # Use client credentials flow
                print("Flujo: APP-ONLY (client credentials) con ConfidentialClientApplication")
                result = self.app.acquire_token_for_client(scopes=self.scopes)
            else:
                print("Flujo: DELEGADO (device code) con PublicClientApplication")
                # Use device code flow
                print("\nIniciando flujo de autenticación con dispositivo...")
                flow = self.app.initiate_device_flow(scopes=self.scopes)
                
                if "user_code" not in flow:
                    error_msg = f"Error al iniciar flujo de autenticación: {json.dumps(flow, indent=2)}"
                    print("\n¡Error!" + "!"*50)
                    print(error_msg)
                    print("!"*50 + "\n")
                    raise Exception(error_msg)
                
                # Mostrar instrucciones al usuario
                print("\n" + "="*80)
                print("PARA AUTENTICARSE, SIGA ESTOS PASOS:")
                print("1. Abra el navegador y vaya a:", flow["verification_uri"])
                print("2. Ingrese el siguiente código:", flow["user_code"])
                print("3. Asegúrese de iniciar sesión con la cuenta:", self.app.client_id)
                print("="*80 + "\n")
                
                # Esperar a que el usuario complete la autenticación
                print("Esperando autenticación...")
                result = self.app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                print("\n¡Autenticación exitosa!")
                print(f"Token expira en: {result.get('expires_in', 'desconocido')} segundos")
                print("Guardando token en caché...")
                self._save_token_cache()
                return result["access_token"]
            else:
                error = result.get("error", "Error desconocido")
                error_desc = result.get("error_description", "Sin descripción")
                error_msg = f"Error al obtener token: {error} - {error_desc}"
                
                print("\n" + "!"*80)
                print("ERROR DE AUTENTICACIÓN")
                print("-"*80)
                print(f"Error: {error}")
                print(f"Descripción: {error_desc}")
                print("""
Posibles causas:
1. El código de verificación expiró (válido por 15 minutos)
2. No se concedieron los permisos necesarios
3. Problemas de red o con el servidor de autenticación
4. La aplicación no tiene los permisos configurados correctamente en Azure AD
""")
                print("!"*80 + "\n")
                
                raise Exception(error_msg)
                
        except Exception as e:
            print("\n" + "="*80)
            print("ERROR DETALLADO")
            print("-"*80)
            print(f"Tipo de error: {type(e).__name__}")
            print(f"Mensaje: {str(e)}")
            print("\nInformación de depuración:")
            print(f"- Scopes: {self.scopes}")
            print(f"- Authority: {self.authority}")
            print(f"- Client ID: {self.client_id}")
            print(f"- Cache path: {os.path.abspath(self.token_cache_path) if self.token_cache_path else 'No configurado'}")
            print("="*80 + "\n")
            
            # Proporcionar instrucciones de solución de problemas
            print("""
PASOS PARA SOLUCIONAR EL PROBLEMA:
1. Verifica que la aplicación esté registrada correctamente en Azure AD
2. Asegúrate de que los siguientes permisos estén configurados:
   - Mail.Send (delegado)
   - User.Read (delegado)
3. Verifica que el usuario tenga los permisos necesarios en Office 365
4. Intenta eliminar el archivo de caché y volver a autenticarte
""")
            
            raise
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        from_email: Optional[str] = None,
        content_type: str = "Text"
    ) -> bool:
        """
        Send an email using Microsoft Graph API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Email body content
            from_email: Sender email address (required for client credentials flow)
            content_type: Content type ('Text' or 'HTML')
            
        Returns:
            bool: True if email was sent successfully, False otherwise
            
        Raises:
            Exception: If there's an error sending the email
        """
        try:
            # Get access token
            access_token = self._get_token()
            if not access_token:
                raise Exception("No se pudo obtener un token de acceso válido")

            # Determine the endpoint based on authentication flow
            if self.client_secret:
                # For client credentials flow, we need to use the user's UPN in the URL
                if not from_email:
                    raise ValueError("Se requiere el parámetro 'from_email' cuando se usa el flujo de credenciales de cliente")
                
                # Remove any domain part if it's an email address
                user_principal_name = from_email.split('@')[0] if '@' in from_email else from_email
                endpoint = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"
            else:
                # For delegated flow, we can use /me
                endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"

            # Prepare the email message
            email_msg = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": content_type,
                        "content": message
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ]
                },
                "saveToSentItems": "true"
            }

            # Add from address if specified (for delegated flow)
            if from_email and not self.client_secret:
                email_msg["message"]["from"] = {
                    "emailAddress": {
                        "address": from_email
                    }
                }

            # Send the email
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=email_msg,
                timeout=30
            )

            if response.status_code in (200, 202):
                return True
            else:
                error_msg = f"Failed to send email: {response.status_code} - {response.text}"
                if response.status_code == 403:
                    error_msg += "\nMake sure the application has the 'Mail.Send' application permission and the admin has granted consent."
                raise Exception(error_msg)
                
        except Exception as e:
            print(f"Error al enviar el correo: {str(e)}")
            raise
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Devuelve información del usuario. En app-only consulta /users/{UPN}; en delegado, /me.
        """
        token = self._get_token()
        if not token:
            raise Exception("Failed to get access token")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if self.client_secret:
            # App-only: NO hay contexto de usuario -> /users/{UPN}
            if not hasattr(self, "user_email") or not getattr(self, "user_email", None):
                raise Exception("Para app-only, configure AZURE_USER_EMAIL (UPN) en settings")
            url = f"https://graph.microsoft.com/v1.0/users/{self.user_email}"
        else:
            # Delegado: hay usuario -> /me
            url = "https://graph.microsoft.com/v1.0/me"

        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Failed to get user info: {resp.status_code} - {resp.text}")
        return resp.json()

