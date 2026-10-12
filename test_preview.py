from mcp_utils import launch_music_chat

if __name__ == "__main__":
    print("\n🚀 Iniciando Gradio com gpt-oss:20b...")
    print("👉 Acesse no seu navegador: http://localhost:7860\n")
    # Inicia diretamente com a configuração interna do gpt-oss:20b
    launch_music_chat(share=False)
