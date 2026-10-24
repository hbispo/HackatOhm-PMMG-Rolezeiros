<script setup lang="ts">
import { computed } from 'vue'
import { usePlano } from '../stores/plano'
import { corViatura } from '../cores'
import type { Modo } from '../types'

const plano = usePlano()

const ROTULO_MODO: Record<Modo, string> = {
  ponto_base: 'Ponto-base 20 min + patrulha 40 min (1 km)',
  entorno_2km: 'Patrulhamento no entorno de 2 km',
  entorno_3km: 'Patrulhamento no entorno de 3 km',
}

const cartoes = computed(() => {
  const todos = plano.distribuicao?.cartoes ?? []
  return plano.viaturaSelecionada ? todos.filter((c) => c.viatura_id === plano.viaturaSelecionada) : todos
})

const imprimir = () => window.print()

function nome(id: string) {
  return plano.viaturas.find((v) => v.id === id)?.nome ?? id
}
</script>

<template>
  <section class="cartoes">
    <header>
      <h2>Cartões-Programa <small>({{ cartoes.length }})</small></h2>
      <button @click="imprimir">Imprimir</button>
    </header>
    <article
      v-for="c in cartoes"
      :key="c.viatura_id"
      class="cartao"
      :style="{ borderTopColor: corViatura(c.viatura_id, plano.viaturas) }"
    >
      <h3>{{ nome(c.viatura_id) }}</h3>
      <table>
        <thead>
          <tr><th>Faixa</th><th>Classe</th><th>Atividade</th><th>Quadrícula</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="f in c.faixas"
            :key="f.hora"
            :class="[`classe-${f.classe}`, { ativa: plano.horaSelecionada === f.hora }]"
            @click="plano.horaSelecionada = plano.horaSelecionada === f.hora ? null : f.hora"
          >
            <td>{{ String(f.hora).padStart(2, '0') }}h–{{ String((f.hora + 1) % 24).padStart(2, '0') }}h</td>
            <td><span class="classe">{{ f.classe }}</span></td>
            <td>{{ ROTULO_MODO[f.modo] }}</td>
            <td>{{ f.hex_ponto_base ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<style scoped>
.cartoes { padding: 12px 16px; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--dourado-escuro); margin: 6px 0; }
.cartao { border: 1px solid var(--borda); border-top: 4px solid; border-radius: 6px; margin: 12px 0; padding: 8px 10px; break-inside: avoid; }
h3 { margin: 4px 0 8px; font-size: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--texto-suave); font-weight: 600; border-bottom: 1px solid var(--borda); padding: 4px; }
td { padding: 3px 4px; border-bottom: 1px solid var(--fundo); }
tbody tr { cursor: pointer; }
tr.ativa td { background: #fff3c4; }
.classe { display: inline-block; width: 18px; text-align: center; border-radius: 3px; font-weight: 700; }
.classe-1 .classe { background: #1c1c1c; color: #fff; }
.classe-2 .classe { background: var(--dourado); color: #1c1c1c; }
.classe-3 .classe { background: #e6e1d6; color: #1c1c1c; }
</style>
