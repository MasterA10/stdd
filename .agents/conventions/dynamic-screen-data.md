---
name: dados dinâmicos de telas
description: Contrato compartilhado para identificar e simular dados variáveis das telas.
---

# Dados dinâmicos de telas

Telas devem distinguir texto/aparência invariáveis de dados que podem mudar por
API, banco, sessão, configuração, busca, evento ou cálculo externo.

Para dados variáveis, o projeto mantém um único JSON de mock fake, normalmente
`mock-fake.json` na raiz da aplicação. Cada tela usa uma chave ou caminho explícito
desse arquivo e acessa o payload por uma função com o nome lógico `get_mock_fake`.
Em linguagens que adotam outra convenção de identificadores, somente o casing pode
mudar (`getMockFake`, por exemplo); o nome não deve ser traduzido.

O mock fake é uma fonte temporária para construir e validar a view. No L2, registre
no Draw a chave/caminho e o formato esperado, mas não salve símbolo de
`get_mock_fake` nem da função de leitura do mock. Seu formato deve ser compatível
com a futura fonte real, mas ele não substitui controller, model, persistência,
regras de negócio ou integração. No L3, durante a implementação do backend, salve
somente os símbolos reais das funções, controllers, models e integrações implementados.
