import { useState, useCallback } from 'react';
import { chatbotApi } from '@/api/chatbot';

export const useChatbotStreaming = () => {
  const [streamedContent, setStreamedContent] = useState<Record<string, string>>({});
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);

  const analyzeWithStreaming = useCallback(
    async (
      request: { question: string; history_id?: number },
      messageId: string,
      onComplete?: (response: any) => void
    ) => {
      setStreamingMessageId(messageId);
      setStreamedContent((prev) => ({ ...prev, [messageId]: '' }));

      try {
        const response = await chatbotApi.analyze(request, (chunk) => {
          if (chunk.type === 'content' && chunk.content) {
            setStreamedContent((prev) => ({
              ...prev,
              [messageId]: (prev[messageId] || '') + chunk.content,
            }));
          }
        });

        setStreamingMessageId(null);
        onComplete?.(response);
        return response;
      } catch (error) {
        setStreamingMessageId(null);
        throw error;
      }
    },
    []
  );

  const resetStreaming = useCallback(() => {
    setStreamedContent({});
    setStreamingMessageId(null);
  }, []);

  return {
    streamedContent,
    streamingMessageId,
    analyzeWithStreaming,
    resetStreaming,
  };
};
