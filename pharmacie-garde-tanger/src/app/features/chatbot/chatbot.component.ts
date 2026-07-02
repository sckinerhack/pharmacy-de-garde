import { Component, signal, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  time: string;
}

@Component({
  selector: 'app-chatbot',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chatbot.component.html',
  styleUrl: './chatbot.component.scss'
})
export class ChatbotComponent implements AfterViewChecked {
  @ViewChild('messagesEnd') messagesEnd!: ElementRef;

  isOpen = signal(false);
  isLoading = signal(false);
  inputText = signal('');
  messages = signal<Message[]>([
    {
      role: 'assistant',
      content: 'Salam ! 👋 Je suis votre assistant pharmacie. Je peux vous aider sur :\n\n💊 Médicaments et posologies\n🌿 Conseils santé et prévention\n⚠️ Interactions médicamenteuses\n🏥 Orientation vers les soins\n\nComment puis-je vous aider ?',
      time: this.getTime()
    }
  ]);

  suggestions = [
    'Quels sont les effets secondaires du paracétamol ?',
    'Comment conserver mes médicaments ?',
    'Que faire en cas de fièvre ?',
    'C\'est quoi un antibiotique ?',
  ];

  toggleChat() { this.isOpen.set(!this.isOpen()); }

  getTime(): string {
    return new Date().toLocaleTimeString('fr-MA', { hour: '2-digit', minute: '2-digit' });
  }

  async sendMessage(text?: string) {
    const msg = text || this.inputText().trim();
    if (!msg || this.isLoading()) return;

    this.inputText.set('');

    const newMessages = [...this.messages(), {
      role: 'user' as const,
      content: msg,
      time: this.getTime()
    }];
    this.messages.set(newMessages);
    this.isLoading.set(true);

    try {
      const response = await fetch('http://localhost:3000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          system: `Tu es PharmAssist, un assistant pharmacien expert et bienveillant pour les habitants de Tanger, Maroc.

Ton rôle :
- Répondre aux questions sur les médicaments, posologies, effets secondaires, interactions
- Donner des conseils santé généraux et de prévention
- Informer sur les maladies courantes et leur prise en charge
- Orienter vers un médecin ou urgences quand nécessaire
- Parler des pharmacies de garde à Tanger si demandé

Règles importantes :
- Réponds toujours en français
- Sois clair, concis et rassurant
- Utilise des emojis avec modération pour rendre la réponse lisible
- TOUJOURS rappeler de consulter un médecin pour tout diagnostic
- Ne jamais remplacer un avis médical professionnel
- Pour les urgences graves, orienter vers le SAMU (15) ou CHU Tanger
- Adapte le niveau de langage à un grand public (pas trop technique)
- Structure tes réponses avec des points clairs quand c'est pertinent`,
          messages: newMessages.map(m => ({ role: m.role, content: m.content }))
        })
      });

      const data = await response.json();
      const reply = data.content?.[0]?.text || 'Désolé, je n\'ai pas pu répondre. Réessayez.';

      this.messages.set([...this.messages(), {
        role: 'assistant',
        content: reply,
        time: this.getTime()
      }]);
    } catch {
      this.messages.set([...this.messages(), {
        role: 'assistant',
        content: '⚠️ Une erreur est survenue. Vérifiez votre connexion et réessayez.',
        time: this.getTime()
      }]);
    }

    this.isLoading.set(false);
  }

  onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.sendMessage();
    }
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom() {
    try {
      this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
    } catch {}
  }

  formatMessage(text: string): string {
    return text
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
}
