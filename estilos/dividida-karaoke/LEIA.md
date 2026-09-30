# Dividida Karaokê

Origem: anúncio de referência "D3FSER058 H1" (128 s, 1080×1920), estudado em 2026-09-25 com `scripts/criar_template.py estudar` + leitura de um quadro por bloco de corte. Nicho: saúde/intestino/emagrecimento, expert de terno falando para a câmera.

A cara do vídeo: **o expert em cima e o B-roll embaixo quase o tempo todo**, legenda itálica branca bem na emenda com a palavra que está sendo falada em amarelo, e letreiro condensado em caixa alta só nas palavras de impacto. Ritmo rápido, com cortes secos.

## Ritmo (medido, não no olho)

- 36 blocos em 128 s, 16,4 trocas/min, **mediana de 2,48 s**, mínimo 0,7 s e máximo 15,9 s.
- A meta é a mediana: um B-roll novo a cada 2 a 3 s de fala. O máximo de 15,9 s veio do depoimento (ver Adaptações) e não é ritmo a copiar.
- Quase não tem respiro com a pessoa sozinha na tela. O B-roll muda embaixo enquanto o expert continua em cima, então **dividida → dividida é a passagem normal** (por isso `encadeia` aceita isso e `max_encadeadas` é 10).
- Corte seco como padrão. Nos quadros não aparece whip, glitch, flash, P&B nem holofote. Transição de entrada/saída: `corte`, no máximo `fade` curto.

## Formatos de cena

- **`dividida` sempre invertida**: toda cena `dividida` vai com `inverte=True` e `emenda="reto"` (ex.: `E.broll("dividida", "âncora", broll="ID", trans="corte", saida="corte", inverte=True, emenda="reto")`). Na referência o expert fica em cima (cabeça e ombros) e o B-roll embaixo, com linha de corte reta, sem dissolver. O motor por padrão faz o contrário (B-roll em cima). Sem `inverte=True` a cena fica errada. `dividida.fusao` é 0 pelo mesmo motivo.
  - A emenda da referência fica entre 52% e 55% da altura; a do motor é fixa em 50%. Diferença pequena, aceitável.
- **`canto` na abertura**: logo depois do gancho (quadros 2 a 4, de 2 s a 11 s), o expert aparece recortado na frente de uma anatomia grande (intestino, sistema digestivo), com letreiro colorido do lado. Usar `canto` de 2 s ou mais só nesse trecho de mecanismo inicial. `canto → canto` pode encadear quando a anatomia muda.
- **`cheia`**: (a) cotidiano ou prova social que ocupa a tela (quadros 9 a 11: comida, relógio de jejum, academia); (b) sequência de palavras de mecanismo com anatomia/micro 3D e **uma palavra grande no meio** (quadros 22 a 24: SILENCIAR → EXPURGAR → RECOLONIZAR, uma por cena, estilo `grande`). `cheia → cheia` pode encadear nessa lista.
- Respiro (só a pessoa): raro e curto, geralmente numa frase de autoridade ("ela fazia tudo", "flora de bactérias"). Mínimo de 0,6 s entre formatos que não encadeiam.
- Não usa `card`.

## Legenda

- Karaokê: Poppins Bold Italic 77 px, branca, contorno preto de 4 px e sombra curta. A **palavra falada fica amarela** ([253,253,0]). `legenda.karaoke=true` faz isso sozinho a partir da transcrição.
- Posição fixa: linha de base a 54,5% da altura (medida quadro a quadro: amarelo sempre entre 51,7% e 54,6%). Fica em cima da emenda da dividida e no mesmo lugar em cheia, canto ou só a pessoa: `dividida_dy` e `canto_dy` são 0.
- Grupos de 2 a 3 palavras, no máximo 20 caracteres, em minúsculas como foi falado.
- O estudo automático deu o centro da legenda em 34,9%. Esse número veio do amarelo do letreiro do gancho, não da legenda. O valor certo é o medido nos quadros (54,5%).

## Letreiro

Anton (condensada pesada), caixa alta, entra seco (0,12 s) e pode ficar em cima do B-roll (`letreiro_sobre_broll: true`). Estilos:
- `branca` + `amarela`: frase de gancho ou de contexto, com a palavra-chave em amarelo-ouro ([243,198,13]). Ex.: "VEJA O QUE **BANANA** FAZ / COM O **METABOLISMO LENTO**!". Até 2 linhas e 5 palavras.
- `vermelha`: o problema/culpado ("DA MESMA"). `verde`: a solução ou o resultado ("O CORPO ESTÁ **DESINFLAMADO**", `branca` + `verde`).
- `grande`: uma palavra só, em cheia sobre anatomia (SILENCIAR, EXPURGAR, RECOLONIZAR), a uns 35% da altura.
- Densidade: letreiro não é legenda. Só nas palavras de mecanismo, número ou virada, uns 4 a 6 por minuto. Quando o letreiro repete as palavras faladas, a legenda some sozinha.
- **Na dividida invertida o motor desce o letreiro metade da tela** (vai para o lado do B-roll). Para ele ficar logo abaixo da emenda, como na referência ("DA IDADE OU DA / MENOPAUSA"), use `topo` perto de 0,0 a 0,03 nessas cenas.

## Adaptações (o que a referência tem e o motor não faz)

- **Gancho com faixa preta** (0 a 2 s): na referência, o topo da tela é uma faixa preta com o letreiro e o B-roll (banana) fica embaixo, sem o expert. O motor não tem esse formato. Adaptação: `cheia` com o B-roll do gancho e letreiro `branca` + `amarela` a ~12% da altura (`topo=0.12`). Revisar no editor.
- **Depoimento** (84 s a 115 s): um homem em vídeo de celular, tela cheia, com a legenda preta em caixa queimada no próprio vídeo e o áudio dele. O motor não mistura áudio de B-roll (só voz + efeito) e não desenha caixa preta atrás do texto. Se o anúncio novo tiver depoimento, ele precisa vir montado na gravação principal (A-roll), não como B-roll.
- **Setas vermelhas animadas no CTA** (quadro final, outro apresentador): o motor não faz gráfico animado. Trocar por letreiro curto ("CLIQUE ABAIXO", `vermelha` ou `amarela`) se a fala pedir.
- **Riscos vermelhos em cima da comida/salada** (X em cima do prato): vêm prontos no clipe ou não entram. O motor não desenha isso.
- Letreiro com contorno: o motor faz uma cópia escura do texto com pouco blur, não um traço geométrico. Aproxima, mas não é idêntico.

## Som

Medido: 41 ataques graves e 73 agudos. Os agudos (whoosh/pop) caem em 54% das trocas, os graves em 20%, e 13 de 35 trocas não têm som. Tem ambiência/trilha baixa sob a fala (fundo em -35 dBFS), sem batida regular. O template usa o som padrão automático (`lib/sfx_padrao.py`). A trilha de fundo não é reproduzida (o motor mistura só voz e efeito). Uma regra de som fiel (whoosh em ~metade das trocas de B-roll, nada em todas) depende de um `sfx_regras.py` escrito por um humano.

## Cuidados de conteúdo

Anatomia e micro-organismos ilustram a fala, não provam nada. Não acrescentar resultados, números de quilos, exames ou credenciais que não estejam no roteiro.

## Ressalvas para revisão humana

- Fontes novas trazidas para este template: Anton e Poppins Bold Italic (Google Fonts, licença OFL). Aproximam bem a referência, mas não são identificação garantida.
- O `px` do letreiro (92 e 120) e o `tam` da legenda (77) foram medidos pela largura do texto num quadro de 1080×1920. Conferir no primeiro render.
- `inverte=True` e `emenda="reto"` são por cena. O template não força isso sozinho, então quem monta o plano precisa seguir a regra acima.
