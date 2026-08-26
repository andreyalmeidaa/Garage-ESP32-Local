function definirEstadoVisual(status) {
  const gate = document.getElementById('gateDoor');
  if (!gate) return;

  gate.classList.remove('closed', 'opening', 'open', 'closing', 'stopped');
  const valor = (status || '').toLowerCase();

  if (valor.includes('aberto')) {
    gate.classList.add('open');
    return;
  }
  if (valor.includes('parado')) {
    gate.classList.add('stopped');
    return;
  }
  gate.classList.add('closed');
}

async function enviarComando(acao) {
  const mensagem = document.getElementById('comandoMensagem');
  if (mensagem) mensagem.textContent = 'Enviando comando...';

  animarPortao(acao);

  try {
    const resposta = await fetch(`/api/comando/${acao}`, { method: 'POST' });
    const dados = await resposta.json();

    if (!resposta.ok || !dados.ok) {
      if (mensagem) mensagem.textContent = dados.mensagem || 'Falha ao enviar comando.';
      return;
    }

    atualizarPainel(dados.estado);
    if (mensagem) mensagem.textContent = dados.mensagem;
  } catch (erro) {
    if (mensagem) mensagem.textContent = 'Erro de comunicação com o sistema.';
  }
}

function atualizarPainel(estado) {
  const statusTexto = document.getElementById('statusTexto');
  const ultimoComando = document.getElementById('ultimoComando');
  const ultimaAtualizacao = document.getElementById('ultimaAtualizacao');

  if (statusTexto) statusTexto.textContent = estado.status;
  if (ultimoComando) ultimoComando.textContent = estado.ultimo_comando;
  if (ultimaAtualizacao) ultimaAtualizacao.textContent = estado.ultima_atualizacao;

  definirEstadoVisual(estado.status);
}

function animarPortao(acao) {
  const gate = document.getElementById('gateDoor');
  if (!gate) return;

  gate.classList.remove('closed', 'opening', 'open', 'closing', 'stopped');

  if (acao === 'abrir') {
    gate.classList.add('opening');
    return;
  }

  if (acao === 'fechar') {
    gate.classList.add('closing');
    return;
  }

  gate.classList.add('stopped');
}

document.addEventListener('DOMContentLoaded', () => {
  const statusTexto = document.getElementById('statusTexto');
  definirEstadoVisual(statusTexto ? statusTexto.textContent : 'Fechado');
});
