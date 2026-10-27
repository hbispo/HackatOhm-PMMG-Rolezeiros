<script setup lang="ts">
import { ref } from 'vue'

// Resumo da metodologia para a demo. A versão completa está em docs/solucao.md.
const dialogo = ref<HTMLDialogElement>()
const abrir = () => dialogo.value?.showModal()
const fechar = () => dialogo.value?.close()
</script>

<template>
  <button class="abrir" @click="abrir">Como funciona</button>
  <dialog ref="dialogo" @click.self="fechar">
    <article>
      <header>
        <h2>Como a distribuição funciona</h2>
        <button @click="fechar">Fechar</button>
      </header>

      <h3>1. Malha e pontuação</h3>
      <p>
        A área da 39ª CIA é dividida em 1.069 hexágonos de 200 m. Cada ocorrência de 2025 vai para o seu
        hexágono e soma o peso da natureza (A=4, B=5, C=1, D=1, E=2, F=3), no total e em cada hora do dia.
      </p>

      <h3>2. Classificação</h3>
      <p>
        Os hexágonos com ocorrência são divididos por percentis da pontuação: até 50% <b>baixa</b>,
        50–80% <b>média</b>, 80–95% <b>alta</b> e acima de 95% <b>muito alta</b>. As 24 faixas horárias
        são ordenadas pela pontuação e divididas nas Classes 1, 2 e 3, com 8 faixas cada.
      </p>

      <h3>3. Distribuição das viaturas</h3>
      <p>
        Um k-means ponderado agrupa os hexágonos em uma área para cada viatura disponível. O peso de cada
        hexágono combina:
      </p>
      <ul>
        <li><b>70% prioridade</b>: a pontuação multiplicada pelo fator do nível (1; 1,25; 1,5; 2). É aqui que a classificação orienta as viaturas: os hot spots pesam mais e atraem as viaturas para perto.</li>
        <li><b>30% território</b>: uma parte igual para todo hexágono, para nenhuma região ficar sem viatura.</li>
      </ul>
      <p>
        A carga de cada viatura respeita o seu <b>tipo</b>. A de atendimento pode ser empenhada a qualquer
        momento, então fica com 75% da carga de uma preventiva. Nenhuma viatura foge mais de 25% da sua carga-alvo.
      </p>

      <h3>4. Cartão-Programa</h3>
      <p>
        Em cada faixa, a quadrícula de destaque é o hexágono da área da viatura com mais pontos naquela hora.
        Classe 1: ponto-base de 20 min + 40 min de patrulha em 1 km, sem repetir a quadrícula em faixas seguidas.
        Classe 2: 4 faixas iguais à Classe 1 e 4 de patrulha em 2 km. Classe 3: patrulha em 3 km das
        quadrículas de maior incidência da faixa, ou das da Classe 1 quando não há incidência.
      </p>

      <h3>5. Viatura empenhada</h3>
      <p>
        A viatura sai da estratégia, a área dela fica descoberta e as restantes são redistribuídas a partir
        de onde estavam. O sistema mostra os hexágonos que mudaram de viatura, a cobertura antes e depois e
        os novos cartões. A verificação automática confere as regras do edital a cada mudança.
      </p>
    </article>
  </dialog>
</template>

<style scoped>
.abrir { background: transparent; color: #f4f1ea; border-color: var(--dourado); }
.abrir:hover { background: var(--dourado); color: #1c1c1c; }
dialog { max-width: 680px; width: calc(100% - 32px); border: 0; border-radius: 8px; padding: 0; color: var(--texto); }
dialog::backdrop { background: rgb(0 0 0 / 0.5); }
article { padding: 18px 22px; font-size: 14px; line-height: 1.5; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; font-size: 18px; }
h3 { margin: 16px 0 4px; font-size: 14px; color: var(--dourado-escuro); }
p, ul { margin: 4px 0; }
ul { padding-left: 20px; }
</style>
