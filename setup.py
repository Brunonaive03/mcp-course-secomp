from setuptools import setup, find_packages

setup(
    name='mcp_course_secomp',
    version='0.2.0',
    packages=find_packages(),
    install_requires=[
        'pymongo>=4.0.0',
        'gradio>=4.0.0',
        'openai>=1.0.0',
        'mcp>=2.0.0',
    ],
    description='Utilitários de infraestrutura, LLM, MCP Agent e UI para o minicurso de MCP da Secomp UFPE',
)


