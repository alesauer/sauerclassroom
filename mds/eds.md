# Extração de Design System reutilizável

Analise o arquivo `DESIGN.md` fornecido, que contém a extração visual do site COTEMIG.

Seu objetivo é extrair exclusivamente a identidade visual e transformá-la em um Design System independente, reutilizável em qualquer projeto SaaS.

## 1. Preserve
- Paleta de cores e respectivos códigos HEX.
- Tipografia, famílias, pesos e escalas.
- Espaçamentos e proporções.
- Border radius.
- Sombras e elevação.
- Estilo de botões.
- Estilo de inputs e formulários.
- Cards e superfícies.
- Ícones.
- Estados de interação (hover, focus, active).
- Animações e transições.
- Regras de responsividade.
- Diretrizes de acessibilidade.

## 2. Descarte

- Textos, títulos e conteúdos.
- Estrutura e organização das páginas originais.
- Menus e navegação específicos.
- URLs e referências institucionais.
- Componentes exclusivos do negócio original.
- Variáveis específicas de bibliotecas de terceiros, como SweetAlert2.

## 3. Requisitos

1. Não reproduza o site original.
3. Preserve os valores visuais medidos sempre que forem consistentes.
4. Quando houver contradições nos dados extraídos, identifique-as e recomende um padrão coerente.
5. Não invente informações como se tivessem sido medidas.
6. Separe tokens globais de estilos específicos de componentes.

## 4. Entregáveis

Gere:

- `DESIGN-SYSTEM.md`: documentação completa do sistema visual.
- `tokens.css`: variáveis CSS globais.
- `global.css`: estilos globais.
- `tailwind-theme.css`: configuração de tema para Tailwind CSS v4.
- `COMPONENTS.md`: especificação visual dos componentes.