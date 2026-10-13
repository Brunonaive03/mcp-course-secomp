from setuptools import setup, find_packages

setup(
    name='mcp_course_secomp',
    version='0.3.0',
    packages=find_packages(exclude=['notebooks*', 'data*']),
    install_requires=[
        'pymongo>=4.8.0,<5.0.0',
        'gradio>=4.0.0,<7.0.0',
        'openai>=1.40.0',
        'mcp>=2.3.0,<3.0.0',
    ],
    description='Utilitários de infraestrutura, LLM, MCP Agent e UI para o minicurso de MCP da Secomp UFPE',
)


