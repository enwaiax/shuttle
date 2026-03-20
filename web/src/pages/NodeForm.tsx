import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateNode } from "../api/client";

interface NodeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function NodeForm({ open, onOpenChange }: NodeFormProps) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("22");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const create = useCreateNode();

  function reset() {
    setName("");
    setHost("");
    setPort("22");
    setUsername("");
    setPassword("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate(
      {
        name,
        host,
        port: Number(port),
        username,
        auth_type: "password",
        credential: password,
      },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
        },
      },
    );
  }

  const inputCls =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-gray-200 bg-white p-6 shadow-lg focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-base font-semibold text-gray-900">
              Add Node
            </Dialog.Title>
            <Dialog.Close className="rounded-md p-1 text-gray-400 hover:text-gray-600">
              <X size={16} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-server"
                className={inputCls}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Host
                </label>
                <input
                  required
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder="192.168.1.100"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Port
                </label>
                <input
                  required
                  type="number"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  className={inputCls}
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Username
              </label>
              <input
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="root"
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close className="rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50">
                Cancel
              </Dialog.Close>
              <button
                type="submit"
                disabled={create.isPending}
                className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {create.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
